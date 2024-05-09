import requests 
import pandas as pd
from bs4 import BeautifulSoup
from langchain.docstore.document import Document
import os
import asyncio
import time
import json
from datetime import datetime, timedelta
import re

doc_list = []
class Document:
    def __init__(self, page_content, metadata):
        self.page_content = page_content
        self.metadata = metadata

    def json(self):
        return {
            'page_content': self.page_content,
            'metadata': self.metadata
        }


def getting_all_meta_tags(response):
    soup = BeautifulSoup(response, 'html.parser')
    meta_tags = soup.find_all('meta')
    metadata = {}
    for tag in meta_tags:
        if 'name' in tag.attrs:
            name = tag.attrs['name']
            content = tag.attrs.get('content')
            metadata[name] = content
        elif 'property' in tag.attrs:  # For OpenGraph metadata
            property = tag.attrs['property']
            content = tag.attrs.get('content')
            metadata[property] = content
    return metadata


def html_parser(data):
    html_content = data
    soup = BeautifulSoup(html_content, 'html.parser')
    text = soup.get_text(separator='\n')
    return text

##def clean_text(text):
##    # Remove extra white spaces
##    cleaned_text = re.sub(r'\s+', ' ', text)
##    # Remove new line characters
##    cleaned_text = cleaned_text.replace('\n', ' ')
##    # Remove carriage return characters
##    cleaned_text = cleaned_text.replace('\r', '')
##    return cleaned_text

def clean_text(text):
    # Replace two or more spaces with a single space
    cleaned_text = re.sub(r'\s{2,}', ' ', text)
    # Replace two or more newline or carriage return characters with a single newline character
    cleaned_text = re.sub(r'[\n\r]{2,}', '\n', cleaned_text)
    return cleaned_text

# Example usage:
text_to_clean = "This   is    a     sample\n\n\n\n\n\n\n\n\r\r\r\r\r\r\rtext\r\r\r\r\r\r\rwith multiple   spaces and\n\n\n\n\n\nnewlines."
cleaned_text = clean_text(text_to_clean)
print(cleaned_text)

def getting_all_span_tags(response):
    soup = BeautifulSoup(response, 'html.parser')
    span_tags = soup.find_all('span')


def save_docs_to_json(array: [Document], file_path: str) -> None:
    json_data = [doc.json() for doc in array]
    with open(file_path, 'w') as json_file:
        json.dump(json_data, json_file)


async def updating_datasets_w_reg_interval(page_number, post_number , hour_of_update , minute_for_update):
    after_parser = ''
    
    continue_in_event_loop = False
    pages_api_url = "http://expertflow.com/wp-json/wp/v2/pages?per_page=100&page=" + str(page_number)
    posts_api_url = "http://expertflow.com/wp-json/wp/v2/posts?per_page=100&page=" + str(post_number)
    pages_response = requests.get(pages_api_url)
    posts_response = requests.get(posts_api_url)
    pages_data = pages_response.json()
    posts_data = posts_response.json()

    # Implement Pages api updates
    if type(pages_data) != dict:
        continue_in_event_loop = True
        print("Page # " + str(page_number) + " has data ")
        pages_meta_data = getting_all_meta_tags(pages_response.text)
        pages_span_tags = getting_all_span_tags(pages_response.text)
        print("We've " + str(len(pages_data)) + " pages ")
        for page_data in range(len(pages_data)):
            after_parser = html_parser(pages_data[page_data].get('content')['rendered']).replace('None', '')
            after_parser = clean_text(after_parser)
            link = pages_data[page_data].get('link')
            title = pages_data[page_data].get('title')['rendered']
            doc_list.append(Document(page_content=after_parser, metadata={"source": str(page_data) + " page_source ",
                                                                       "title": title,
                                                                       "link": link,
                                                                       "page_number": str(page_number),"hour_of_update": str(hour_of_update),
                                                                          "minute_for_update":str(minute_for_update)}))
    else:
        if continue_in_event_loop == False:
            print("Page # " + str(page_number) + " has " + str(pages_data['data']['status']) + " code ")
            print("Pages Api now has no data ...")

    # Implementing Posts api updates
    if type(posts_data) != dict:
        continue_in_event_loop = True
        print("Post # " + str(post_number) + " has data ")
        posts_meta_data = getting_all_meta_tags(posts_response.text)
        for data_post in range(len(posts_data)):
            after_parser = html_parser(posts_data[data_post].get('content')['rendered']).replace('None', '')
            after_parser = clean_text(after_parser)
            link = posts_data[data_post].get('link')
            title = posts_data[data_post].get('title')['rendered']
            doc_list.append(Document(page_content=after_parser, metadata={"source": str(data_post) + " post_source ",
                                                                       "title": title,
                                                                       "link": link,
                                                                       "post_number": str(post_number),
                                                                        "hour_of_update": str(hour_of_update),
                                                                          "minute_for_update":str(minute_for_update)}))
        print("We've " + str(len(posts_data)) + " posts ")
    else:
        if continue_in_event_loop == False:
            print("Post # " + str(post_number) + " has " + str(posts_data['data']['status']) + " code ")
            print("Posts Api now has no data ...")

    if continue_in_event_loop == True:
        save_docs_to_json(doc_list, 'general_file_posts_pages.json')
        await updating_datasets_w_reg_interval(page_number + 1, post_number + 1 , hour_of_update , minute_for_update)


def read_json_file(file_path):
    with open(file_path, 'r') as json_file:
        json_data = json.load(json_file)
    return json_data


# Function to calculate the time until next day with entered time
def seconds_until_midnight(hour, minute):
    tomorrow = datetime.now() + timedelta(1)
    midnight = datetime(year=tomorrow.year, month=tomorrow.month, day=tomorrow.day, hour=hour, minute=minute, second=0)
    return (midnight - datetime.now()).total_seconds()


hour_of_update = 0
minute_for_update = 0
# Infinite loop to run the task every day at entered time
while True:
    filePath = "general_file_posts_pages.json"
    if os.path.isfile(filePath):
        #os.remove(filePath)
        print("The File is Existed ... and will be updated Successfully")
        json_data = read_json_file("general_file_posts_pages.json")
        num_pages = [doc for doc in json_data if 'page_number' in doc['metadata']]
        num_posts = [doc for doc in json_data if 'post_number' in doc['metadata']]
        print("Number of pages:", len(num_pages))
        print("Number of posts:", len(num_posts))

        last_page_reached_pages = str(num_pages[len(num_pages)-1]['metadata']['page_number'])
        last_page_reached_posts = str(num_posts[len(num_posts)-1]['metadata']['post_number'])
        print("The Last Number of Pages we've reached : " + last_page_reached_pages)
        print("The Last Number of Posts we've reached : " + last_page_reached_posts)
        print("The File is Existed ... will be updated from Page #"+str(int(last_page_reached_pages)+1)+ " for Pages , and Page #" + str(int(last_page_reached_posts)+1) +" for Posts.")
        hour_of_update = str(num_pages[len(num_pages)-1]['metadata']['hour_of_update'])
        minute_for_update = str(num_pages[len(num_pages)-1]['metadata']['minute_for_update'])
        if 0 <= int(hour_of_update) < 12:
            print("The dataset will be updated daily at "+hour_of_update+":"+minute_for_update+" AM ")
        else:
            print("The dataset will be updated daily at "+hour_of_update+":"+minute_for_update+" PM ")
        asyncio.run(updating_datasets_w_reg_interval(int(last_page_reached_pages)+1 , int(last_page_reached_posts)+1 , hour_of_update, minute_for_update))
    else:
        print("Note: 0 = 12 AM and 1 = 1 AM, therefore, 12 = 12 PM")
        hour_of_update = input("Enter the hour for update: ")
        minute_for_update = input("Enter the minutes of update hour: ")
        asyncio.run(updating_datasets_w_reg_interval(1, 1 , hour_of_update , minute_for_update))

        
    # Get the number of seconds until midnight
    sleep_time = seconds_until_midnight(int(hour_of_update), int(minute_for_update))
    # Perform the task
    print("Our Data Updated successfully ...")
    # Sleep until entered time
    time.sleep(sleep_time)


