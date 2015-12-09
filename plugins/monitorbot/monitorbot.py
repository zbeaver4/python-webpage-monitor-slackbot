import requests
import glob
import re
import yaml
import dill
import os
import string
from bs4 import BeautifulSoup
from slackclient import SlackClient

#initialize lists pertaining to ouputs to be passed to rtmbot.py
crontable = []
outputs = []

#Grab configuration options for slackbot
config = yaml.load(file('rtmbot.conf', 'r'))
trig_word = config["TRIGGER_WORD"].lower()

def visible(element):
    if element.parent.name in ['style', 'script', '[document]', 'head', 'title']:
        return False
    elif re.match('<!--.*-->', str(element)):
        return False
    return True

def concat_text(text):
    '''concatenates text for display (200 character max) if it's too long'''
    if len(text) > 200:
        text = text[:200] + '...'
    return text

def dill_kill():
    '''Searches for all files with the extension *.dill
    in the current directory and deletes them'''
    for currentFile in glob.glob(os.path.join('webpage_cache', '*')):
        if currentFile.endswith('dill'):
            os.remove(currentFile)

def strip_url(url):
    '''Takes a URL string and removes non alphanumeric characters'''
    
    return re.sub('[\W_]+', '', url)

def dill_soup(bs4_obj, url):
	'''Serializes a beautifulsoup object after converting it to a string.
     saves the file using the url'''
 
	dill_file = os.path.join('webpage_cache', strip_url(url) + '.dill')
	with open(dill_file, 'wb') as f:
		dill.dump(str(bs4_obj), f)

def undillify(url, str_version = False):
    '''Reads back in a serialized object matching the filename of the given url'''
    
    fn = os.path.join('webpage_cache', strip_url(url) + '.dill')
    string_version = dill.load(open(fn, 'rb'))
    
    if str_version:
        return string_version
    else:
        return BeautifulSoup(string_version)

def grab_whole_web_page(url):
	'''Grabs the entire web page of the give URL. Returns 
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

def check_initialization(url):
    '''Checks if monitoring of URL has been initialized (checks dill)'''
    
    stripped_url = re.sub('[\W_]+', '', url)
    if os.path.isfile(os.path.join('webpage_cache', stripped_url + '.dill')):
		return True
    else:
		return False

def monitor_whole_page(message):
    '''Function that monitors the whole page for updates'''    
    
    #split the message to anlayze individual pieces
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

def monitor_id(message):
    '''Monitors webpage text associated with a specific id for changes'''
    
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
                    
                    id_text = str(filter(lambda x:x in string.printable, id_text)) #get rid of any weird unicod
                    
                    #Check if the initialization has already started. If so, check for differences and replace if necessary
                    if check_initialization(url):
                        
                        #Check if there's a difference in the web pages
                        if id_text != undillify(url, str_version = True):
                            
                            #Store update text
                            dill_soup(id_text, url)
                            
                            #concatenate text if necessary
                            id_text = concat_text(id_text)
                            return url + ' with id *' + web_id + '* has been updated! New text:\n \"' + id_text + '\"'
                            
                    #When it hasn't been initialized
                    else:
                        
                        #Store the id's text
                        dill_soup(id_text, url)
                        
                        #concatenate text if necessary
                        id_text = concat_text(id_text)
                        return 'Now monitoring url ' + url + ' with id *' + web_id + '* having text:\n \"' + id_text + '\"'
        
        #When something goes wrong trying to pull down the webpage with beautiful soup
        else:
            return 'There was an error accessing ' + url + '. Error: ' + str(da_soup)

def process_message(data):
    """Process a message entered by a user
    If the message has either the trigger word, 
    evaluate it and respond by starting to monitor the page

    data -- the message's data
    """
    message = data["text"]
    first_word = message.split()[0].lower()
    rest_of_message = re.sub(first_word, '', message)
    
    # Look for trigger word, remove it, and look up each word
    if trig_word == first_word:
        
        print message
        rest_of_message = rest_of_message.lower()
        outputs.append([data['channel'], monitor_whole_page(rest_of_message)])
    
    elif first_word == 'quit_monitor':
        
        print message
        dill_kill()
        outputs.append([data['channel'], 'Web page monitoring has been stopped.'])
    
    elif first_word == 'monitor_id':
        
        print message
        outputs.append([data['channel'], monitor_id(rest_of_message)])