class EI_Access:
    def __init__(self):

        self.version=None # "3.11" for example 
        self.system_model=None # "cutoff" for example
    
        #Fill if you have a local database
        self.path = None # Local folder with ecoinvent

        #Fill if you want to download the database
        self.username = None
        self.password = None
