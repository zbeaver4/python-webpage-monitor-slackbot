###next step: get bot working with whole page###

###Testing Ground###
data = {"text": "monitor https://news.ycombinator.com/"}
config = yaml.load(file('C:\\Users\\zacharybeaver\\Documents\\GitHub\\python-WebPageMonitorBot\\rtmbot.conf', 'r'))
url = 'https://news.ycombinator.com/'

###Function to strip urls
def strip_url(url):
	return re.sub('[\W_]+', '', url)

###Function to check if monitoring has been initialized (check Pickle)###
def check_initialization(url):
	stripped_url = strip_url(url)
	if os.path.isfile(stripped_url + '.pickle'):
		return True
	else:
		return False

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

##Testing
with open(strip_url(url) + '.pickle', 'r') as f:
	poop2 = pickle.load(f)

###Function to compare the current soup object with the pickled soup object

###Function to grab the info from the input URL (id search)###

###Function to grab the info from the input URL (text search)###

###Function to save beautifulsoup object to a file to be called later###

###Function to stop web monitoring for given URL(delete pickle file if exists)
