import random
import glob
from time import sleep
import requests
import time
import re
import string
import yaml
import dill
import datetime as dt
import numpy as np
import os
from bs4 import BeautifulSoup
from slackclient import SlackClient

crontable = []
outputs = []

config = yaml.load(file('rtmbot.conf', 'r'))
trig_word = config["TRIGGER_WORD"].lower()

#==============================================================================
# ###Testing Ground###
# data = {"text": "monitor https://news.ycombinator.com/"}
# url = 'https://news.ycombinator.com/'
#==============================================================================

###Function to concatenate text for display if it's too long
def concat_text(text):
    if len(text) > 200:
        text = text[:200] + '...'
    return text

###Function to grab the info from the input URL (id search)###
def monitor_id(message):
    
    #Case 1: check for valid url
    word_list = message.split()
    
    #only handling one web page at a time at this point
    if len(word_list) != 2:
        return "Incorrect number of parameters for monitor_id!"
    
    #Everything's good so far...try to get the webpage and monitor
    else:
        url = re.sub('<|>', '', word_list[0]).split('|')[0]
        web_id = word_list[1]
        da_soup = grab_whole_web_page(url)
        
        #Successfully grabbed the web page
        if type(da_soup) is BeautifulSoup:
            
            #Check if id exists in webpage
            html_element = da_soup.find(id = web_id)
            if html_element is None:
                return "Could not find id " + web_id + " in webpage " + url
            
            else:
                
                #Get the content to be monitored
                id_text = html_element.text
                
                #Check to make sure text is available
                if id_text is None:
                    return 'Found element but no associated text for ' + url + ' with id ' + web_id
                
                #Text is present. Proceed.
                else:
                    
                    id_text = str(id_text)
                    #Check if the initialization has already started. If so, check for differences and replace if necessary
                    if check_initialization(url):
                        
                        #Check if there's a difference in the web pages
                        if id_text != undillify(url, str_version = True):
                            
                            #Store update text
                            dill_soup(id_text, url)
                            
                            #concatenate text if necessary
                            id_text = concat_text(id_text)
                            return url + ' with id ' + web_id + ' has been updated! New text:\n \"' + id_text + '\"'
                            
                    #When it hasn't been initialized
                    else:
                        
                        #Store the id's text
                        dill_soup(id_text, url)
                        
                        #concatenate text if necessary
                        id_text = concat_text(id_text)
                        return 'Now monitoring url ' + url + ' with id ' + web_id + ' having text\n \"' + id_text + '\"'
        
        #When something goes wrong trying to pull down the webpage with beautiful soup
        else:
            return 'There was an error accessing ' + url + '. Error: ' + str(da_soup)

#==============================================================================
# ###unit tests###
# message1 = 'hello ' + web_id #should throw access error
# message2 = 'http://news.ycombinator.com hello ' + web_id #should throw too many params error
# message3 = 'http://news.ycombinator.com asdied' #should throw bad id error
# message4 = 'http://news.ycombinator.com ' + web_id #should initialize (and then show update when it updates)
#==============================================================================

###Function to grab the info from the input URL (text search)###


###Function to delete cached webpages once done monitoring
def dill_kill():
    '''Searches for all files with the extension *.dill
    in the current directory and deletes them'''
    for currentFile in glob.glob(os.path.join('webpage_cache', '*')):
        if currentFile.endswith('dill'):
            os.remove(currentFile)

###Function to strip urls
def strip_url(url):
	return re.sub('[\W_]+', '', url)

###Function to serialize the bs4 object
def dill_soup(bs4_obj, url):
	
	dill_file = os.path.join('webpage_cache', strip_url(url) + '.dill')
	with open(dill_file, 'wb') as f:
		dill.dump(str(bs4_obj), f)

###Read back in the dill object
def undillify(url, str_version = False):
    fn = os.path.join('webpage_cache', strip_url(url) + '.dill')
    string_version = dill.load(open(fn, 'rb'))
    
    if str_version:
        return string_version
    else:
        return BeautifulSoup(string_version)

###Function to grab the info from the input URL (whole page)###
def grab_whole_web_page(url):
	'''Grabs the entire web page. Returns 
	beautiful soup object or different error codes depending on what happens'''
	
	try:
		result = requests.get(url)
		
	except:
		return "Error retrieving URL with requests package"
		
	#Check status code
	if result.status_code != 200:
		return "Error: Status Code " + str(result.status_code)
	
	else:
		soup = BeautifulSoup(result.content)
		return soup

###Function to check if monitoring has been initialized (check Pickle)###
def check_initialization(url):
	stripped_url = re.sub('[\W_]+', '', url)
	if os.path.isfile(os.path.join('webpage_cache', stripped_url + '.dill')):
		return True
	else:
		return False



def process_message(data):
    """Process a message entered by a user
    If the message has either the trigger word, 
    evaluate it and respond by starting to monitor the page

    data -- the message's data
    """
    message = data["text"].lower()
    first_word = message.split()[0].lower()
    rest_of_message = re.sub(first_word, '', message)
    
    # Look for trigger word, remove it, and look up each word
    if trig_word == first_word:
        
        print message
        outputs.append([data['channel'], monitor_whole_page(rest_of_message)])
    
    elif first_word == 'quit_monitor':
        
        print message
        dill_kill()
        outputs.append([data['channel'], 'Web page monitoring has been stopped.'])
    
    elif first_word == 'monitor_id':
        
        print message
        outputs.append([data['channel'], monitor_id(rest_of_message)])
    
    elif first_word == 'monitor_text':
        
        print message
        outputs.append([data['channel'], monitor_text(rest_of_message)])

def monitor_whole_page(message):
    '''Function that monitors the whole page for updates'''    
    
    word_list = message.split()
    
    #only handling one web page at a time at this point
    if len(word_list) >= 2:
        return "I can only monitor one website at a time!"
    
    #Everything's good so far...try to get the webpage and monitor
    else:
        url = re.sub('<|>', '', word_list[0]).split('|')[0]
        da_soup = grab_whole_web_page(url)
        
        #Successfully grabbed the web page
        if type(da_soup) is BeautifulSoup:
            
            #Check if the initialization has already started. If so, check for differences and replace if necessary
            if check_initialization(url):
                
                #Check if there's a difference in the web pages
                if str(da_soup) != str(undillify(url)):
                    dill_soup(da_soup, url)
                    return url + ' has been updated!'
            
            #First time monitoring this page
            else:
                dill_soup(da_soup, url)
                return 'Started monitoring ' + url
        
        #When something goes wrong trying to pull down the webpage with beautiful soup
        else:
            return 'There was an error accessing ' + url + '. Error: ' + str(da_soup)
                
def find_quote(word):
    """Given an individual symbol, 
    find and return the corresponding financial data

    word -- the symbol for which you're finding the data (ex. "GOOG")
    """
    cleanword=re.sub('[@<>]', '', word)
    share = Share(cleanword)
    price = share.get_price()
    if price != None:
        
        # Extract data
        day_high = share.get_days_high()
        day_low = share.get_days_low()
        market_cap = share.get_market_cap()
        year_high = share.get_year_high()
        year_low = share.get_year_low()
        yoy = calculate_YoY(share)
        
        output_string = ('*Stock*: \'{}\' \n*Current Price*: ${} \n*Day Range*: '
        '${} - ${} \n*52 Wk Range*: ${} - ${} \n*YoY Change*: {}\n*Market Cap*: ' 
        '${}').format(word.upper(), str(price), str(day_low), str(day_high), 
                      str(year_low), str(year_high), str(yoy), str(market_cap))
    else:
        output_string = "Can't find a stock with the symbol \'" + cleanword.upper() + "\'"
    return output_string
                               
def calculate_YoY(share):
    """For a given stock, return the year-over-year change in stock price

    share -- the Yahoo Finance Share object for the stock in question
    """
    
    # Get old closes from Yahoo
    year_ago_start = "{:%Y-%m-%d}".format(dt.date.today() - dt.timedelta(days=365))
    year_ago_end = "{:%Y-%m-%d}".format(dt.date.today() - dt.timedelta(days=363))

    old_list = share.get_historical(year_ago_start, year_ago_end)
    if len(old_list) == 0:
        return "NA"
    
    # Get close from a year ago, or if that was a weekend/unavailable, the next most recent closing price
    old = float(old_list[-1]['Close'])    
    new = float(share.get_price())
        
    # Calculate YoY
    delta = int(round((new - old) / old * 100,0))
    if delta > 0:
        yoy = "+" + str(delta) + "%"
    else:
        yoy = str(delta) + "%"
    return yoy

def find_range(message):
    """Returns the average price for a stock over a given time period

    message -- the input message, which should look like 
               "range [ticker symbol] [start date Y-M-D] [end date Y-M-D]" 
               ex. "range GOOG 2014-11-30 2015-11-30" 
    """

    tline = message.split()
    ticker = tline[1]
    date_start = tline[2]
    date_end = tline[3]
    
    # Catch poorly formatted inputs
    if len(tline) != 4 or tline[0] != "range":
            return ('Incorrect range input. '
                    'Try: \'range [ticker symbol] [start date Y-M-D] [end date Y-M-D]\' \n'
                    'Ex. \'range GOOG 2014-11-30 2015-11-30\'')
    
    # Get stock info from Yahoo, catching bad stock symbol inputs
    share = Share(ticker)
    if share.get_price() is None:
        return "Couldn't recognize input symbol: \'" + ticker.upper() + "\'"

    # Get historical information, catching date errors
    try:
        days = share.get_historical(date_start, date_end)
    except:
        return ('Couldn\'t find historical data for date range {} to {} for {}. '
                'Did you input those dates right?').format(date_start, date_end, ticker.upper())             

    # Return average price over the days
    output_string = 'The average closing price for \'{}\' from {} to {} is: ${}'.format(
        ticker.upper(), date_start, date_end,
        str(round(np.mean([float(day['Close']) for day in days]),2)))
    return output_string
