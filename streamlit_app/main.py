import streamlit as st
import pandas as pd
import numpy as np
from serpapi import GoogleSearch
import time

# functions
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


def search_jobs(search,API_key,location):


    params = {
	'api_key': API_key,    		# your serpapi api
	# https://site-analyzer.pro/services-seo/uule/
	#'uule': 'w+CAIQICIaQXVzdGluLFRleGFzLFVuaXRlZCBTdGF0ZXM',		# encoded location 
    'location': location, # retrieve location UK 
    'tbs': 'date_posted:week', # result posted in the last week --> don't think it works
	'q': search,              		# search query
    'hl': 'en',                         		# language of the search
    'gl': 'uk',                         		# country of the search
	'engine': 'google_jobs',					# SerpApi search engine
	'start': 0									# pagination
    }

    df = pd.DataFrame() # empty df
    search = GoogleSearch(params)
    result = search.get_dict()
    df_temp = pd.DataFrame.from_dict(result['jobs_results'])
    df_temp['search_term'] = result['search_parameters']['q']
    df = pd.concat([df, df_temp], ignore_index=True)

    
    return df

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

# start of app

st.image('jon-tyson-7VtLvckhgOU-unsplash.jpg')

st.title("Find vacancies")
st.header("This app allows you to search google and find job postings")
search_text=st.text_area("Type your search below:")
location=st.text_area("Type location below:")

if search_text and location: 
    keywords = get_keywords('keywords.csv')
    API_key = get_serpapi_key('serpapikey.txt')


    # progress bar
    st.balloons()
    st.progress(10)
    with st.spinner('Wait while I find what vacancies are available...'):
        # run google search
        df = search_jobs(search_text, API_key, location)

    # clean up dataframe
    df = remove_senior_jobs(df)
    df = find_skills(df,keywords)
    df = extensions_cleaning(df)

    st.dataframe(df)
