import pandas as pd
import numpy as np
from serpapi import GoogleSearch
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import gspread_dataframe as gd
from gspread_dataframe import set_with_dataframe
from gspread_formatting.dataframe import format_with_dataframe


def get_serpapi_key(api_text_file):
    text_file = open(api_text_file, "r")
    #read whole file to a string
    API_key = text_file.read()
    #close file
    text_file.close()

    return API_key

def get_keywords(keywords_file):
    keywords = pd.read_csv(keywords_file)

    return keywords

def remove_senior_jobs(df):
    # remove positions containing word 'Senior' or 'Principal'

    df=df[df['title'].str.contains('Senior|Principal|Lead')==False].reset_index(drop=True)

    return df

def find_skills(jobs,keys):
    df = jobs


    df['description2'] = df['description'].str.lower()
    df['description2'] = df['description2'].str.replace('/',' ')

    df2 = keys.groupby('keywords').apply(lambda x: x['keywords'].unique())
    for keyword in df2.index:
        df[keyword] = ''

    for col in df2.index:
        df[col] = np.where(df.description2.str.contains('|'.join(df2[col])),1,0)


    df["skills"] = df.apply(lambda x: ','.join(x.index[x == 1]), axis=1)

    df = df[["title","company_name","location","via","skills","description","extensions","job_id",'search_term']]

    return df

def set_searches():
    #list of companies
    comp=['Sky', 'Cognizant', 'HSBC']
    #comp = ['Sky']

    #list of pathways
    path=['Data','Software','Cloud']
    #path= ["Data"]

    # search texts examples
    search_text=[]

    for c in comp:
        for p in path:
            search_text.append(c+ ' '+p + ' jobs')

    return search_text


def search_jobs(search,API_key):


    params = {
	'api_key': API_key,    		# your serpapi api
	# https://site-analyzer.pro/services-seo/uule/
	#'uule': 'w+CAIQICIaQXVzdGluLFRleGFzLFVuaXRlZCBTdGF0ZXM',		# encoded location 
    'location': 'United Kingdom', # retrieve location UK 
    'tbs': 'date_posted:week', # result posted in the last week --> don't think it works
	'q': search,              		# search query
    'hl': 'en',                         		# language of the search
    'gl': 'uk',                         		# country of the search
	'engine': 'google_jobs',					# SerpApi search engine
	'start': 0									# pagination
    }
    return params
    


def search_all_jobs(search_text,API_key):
    # run the search with specific parameters
    df = pd.DataFrame() # empty df

    for s in search_text:
        search = GoogleSearch(search_jobs(s,API_key))
        result = search.get_dict()
        df_temp = pd.DataFrame.from_dict(result['jobs_results'])
        df_temp['search_term'] = result['search_parameters']['q']
        
        df = pd.concat([df, df_temp], ignore_index=True)

    return df

def login_to_google(json_file):
    scope_app =['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive'] 
    cred = ServiceAccountCredentials.from_json_keyfile_name(json_file, scope_app) 
    client = gspread.authorize(cred)

    return client

def save_to_google(google_file_name,sheet_name,client,df):
    # defining the scope of the application
    #credentials to the account
    

    # authorize the clientsheet 
    # open the worksheet
    worksheet = client.open(google_file_name).worksheet(sheet_name)

    # upload df to worksheet
    set_with_dataframe(worksheet, df)

    # set first row as header
    format_with_dataframe(worksheet, df, include_column_header=True)


def extensions_cleaning(df):
    df['extensions'] = df['extensions'].astype("string")
    df[['posted_days_ago','type']]=df['extensions'].str.split(',', 1, expand=True)
    df.fillna(value=pd.np.nan, inplace=True)
    df.fillna('No info',inplace=True)
    for i in range(df.shape[0]):
        if any(map(str.isdigit, df.posted_days_ago[i]))==False:
            df.type[i]=df.posted_days_ago[i]
            df.posted_days_ago[i]=None

    df['posted_days_ago'] = df['posted_days_ago'].str.replace("[","")
    df['posted_days_ago'] = df['posted_days_ago'].str.replace("'","")
    df['posted_days_ago'] = df['posted_days_ago'].str.replace("]","")
    df['type'] = df['type'].str.replace("]","")
    df['type'] = df['type'].str.replace("[","")
    df['type'] = df['type'].str.replace("'","")

    df['posted_days_ago'] = df['posted_days_ago'].fillna("0")
    df.loc[df['posted_days_ago'].str.contains('day'), 'time_type'] = 1
    df.loc[df['posted_days_ago'].str.contains('month'), 'time_type'] = 31
    df.loc[df['posted_days_ago'].str.contains('hour'), 'time_type'] = 0
    df['time_type'] = df['time_type'].fillna("40")
    df['posted_days_ago'] = df['posted_days_ago'].str.extract('(\d+)')
    df["posted_days_ago"] = pd.to_numeric(df["posted_days_ago"])
    df["time_type"] = pd.to_numeric(df["time_type"])
    df['posted_days_ago'] = df['posted_days_ago']*df['time_type']
    df.loc[df['time_type'] == 40, 'posted_days_ago'] = 40

    df['posted_days_ago'] = df['posted_days_ago'].astype(int)
    df['date_posted'] = pd.to_datetime('today').normalize() - pd.to_timedelta(df['posted_days_ago'], unit='d')

    return df


def search_term_cleaning(df):
    df.loc[df['search_term'].str.contains('Data'), 'pathway'] = "Data"
    df.loc[df['search_term'].str.contains('Software'), 'pathway'] = "Software"
    df.loc[df['search_term'].str.contains('Cloud'), 'pathway'] = "Cloud"

    return df