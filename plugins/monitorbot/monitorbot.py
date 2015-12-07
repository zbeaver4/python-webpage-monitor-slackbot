import random
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
from yahoo_finance import Share

crontable = []
outputs = []

config = yaml.load(file('rtmbot.conf', 'r'))
trig_word = config["TRIGGER_WORD"].lower()

###Testing Ground###
cd 'C:\Users\zacharybeaver\Documents\GitHub\python-WebPageMonitorBot'
data = {"text": "monitor https://news.ycombinator.com/"}
url = 'https://news.ycombinator.com/'

check_initializaton(url)

###Function to strip urls
def strip_url(url):
	return re.sub('[\W_]+', '', url)

###Function to serialize the bs4 object
def dill_soup(bs4_obj, url):
	
	dill_file = strip_url(url) + '.dill'
	with open(dill_file, 'wb') as f:
		dill.dump(str(bs4_obj), f)

###Read back in the dill object
def undillify(url):
	fn = strip_url(url) + '.dill'
	string_version = dill.load(open(fn, 'rb'))
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
	if os.path.isfile(stripped_url + '.pickle'):
		return True
	else:
		return False

def process_message(data):
    """Process a message entered by a user
    If the message has either the trigger word or "range", 
    evaluate it and respond accordingly with the stock info 
    or average price over the range

    data -- the message's data
    """
    message = data["text"].lower()
    first_word = message.split()[0].lower()
    
    # Look for trigger word, remove it, and look up each word
    if trig_word == first_word:
        print message
        rest_of_message = re.sub(trig_word, '', message)
        tline=rest_of_message.split()
        if len(tline) >= 10:
            outputs.append([data['channel'], "Too many stocks to look up! Try again with fewer than 10."])
        else:
            for word in tline:
                outputs.append([data['channel'], find_quote(word)])

    elif "range" == first_word:
        print message
        outputs.append([data['channel'], find_range(message)])
                
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
