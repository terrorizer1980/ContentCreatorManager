'''
Created on Feb 24, 2022

@author: tiff
'''
import contentcreatormanager.platform.platform
import contentcreatormanager.media.video.lbry
import requests

class LBRY(contentcreatormanager.platform.platform.Platform):
    '''
    classdocs
    '''
    API_URL = "http://localhost:5279"

    def __get_channel(self):
        params = {
            'claim_id':self.id
        }
        result = requests.post(LBRY.API_URL, json={"method": "channel_list", "params": params}).json()
        if self.check_request_for_error(result):
            raise Exception()
        return result
    
    def __add_channel_videos(self):
        params = {
            "channel_id": [self.id],
            "order_by":'name'
        }
        #grab first page of data for api call to get all claims assosiated with lbry channel
        intial_result = requests.post(LBRY.API_URL, json={"method": "claim_list", "params": params}).json()
        if self.check_request_for_error(intial_result):
            raise Exception()
        
        #stores num of pages and items total returned
        page_amount = intial_result['result']['total_pages']
        item_amount = intial_result['result']['total_items']
        
        self.logger.info(f"Found {item_amount} claims on channel {self.id} with {page_amount} page(s) of data")
        
        pages = []
        claims = []
        
        self.logger.info("adding initial request as 1st page of data")
        pages.append(intial_result['result']['items'])
        
        # if there is more than 1 page of data grab the rest
        if page_amount > 1:
            for x in range(page_amount-1):
                params = {
                    "page":x+2, 
                    "channel_id": [self.id],
                    "order_by":'name'      
                }
                self.logger.info(f"getting page {x+2} of data and adding it")
                current_result = requests.post(LBRY.API_URL, json={"method": "claim_list", "params": params}).json()
                pages.append(current_result['result']['items'])
        
        #loops through to get all the claims that are of type video and adds them to claims list    
        page = 0
        x = 0
        for p in pages:
            page += 1
            for i in p:
                x += 1
                if i['value']['stream_type'] == 'video':
                    self.logger.info(f"Adding claim with claim_id {i['claim_id']} and name {i['name']} from page {page} of the results")
                    claims.append(i)
                else:
                    self.logger.info(f"claim {i['name']} is a {i['value']['stream_type']} not a video.  Not adding it")
        
        claims_before = len(self.media_objects)
        
        #loops through the claims turns them into lbry video objects and adds them as media to the platform
        for c in claims:
            v = contentcreatormanager.media.video.lbry.LBRYVideo(ID=c['claim_id'], settings=self.settings, lbry_channel=self, request=c)
            
            self.add_media(v)
        
        num_vids_added = len(self.media_objects) - claims_before
        self.logger.info(f"Total of {num_vids_added} LBRY Video Objects added to media_objects list")

    def __init__(self, settings : contentcreatormanager.config.Settings, ID : str, init_videos : bool = False):
        '''
        Constructor
        '''
        super(LBRY, self).__init__(settings=settings, ID=ID)
        self.logger = self.settings.LBRY_logger
        self.logger.info("Initializing Platform Object as LBRY Platform object")
        
        #storing result of an api call to get LBRY channel data based on id to finish initializing the object
        result = self.__get_channel()
        
        self.logger.info("Setting address, bid, name, normalized_name, permanent_url, description, email, title, languages, tags, and thumbnail based on api call results")
        self.address = result['result']['items'][0]['address']
        self.bid = result['result']['items'][0]['amount']
        self.name = result['result']['items'][0]['name']
        self.normalized_name = result['result']['items'][0]['normalized_name']
        self.permanent_url = result['result']['items'][0]['permanent_url']
        self.description = result['result']['items'][0]['value']['description']
        self.email = result['result']['items'][0]['value']['email']
        self.title = result['result']['items'][0]['value']['title']
        
        if 'languages' in result['result']['items'][0]['value']:
            self.languages = result['result']['items'][0]['value']['languages']
        else:
            self.languages = ['en']
        if 'tags' in result['result']['items'][0]['value']:
            self.tags = result['result']['items'][0]['value']['tags']
        else:
            self.tags = []
        if 'thumbnail' in result['result']['items'][0]['value']:    
            self.thumbnail = result['result']['items'][0]['value']['thumbnail']
        else:
            self.thumbnail = None
            
        if init_videos:
            self.logger.info("init_videos set to true grabbing video data and adding to media_objects")
            self.__add_channel_videos()
            
        self.logger.info("LBRY Platform object initialized")
        
    def check_request_for_error(self, request):
        if 'error' in request:
            self.logger.error("API call returned an error:")
            self.logger.error(f"Error Code: {request['error']['code']}")
            self.logger.error(f"Error Type: {request['error']['data']['name']}")
            self.logger.error(f"Error Message: {request['error']['message']}")
            return True
        return False