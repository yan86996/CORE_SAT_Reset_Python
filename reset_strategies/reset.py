class Reset:
    """ This class implements the trim and reSP0nd
    reset control strategy according to the Tailer
    Engineering Sequence of Operations. (SOO)
    The default values represent an example of a
    duct static pressure reset strategy.

    Fields at instantiation are as described in
    SOO for ease of use:
    SPmin	Minimum setpoint
    SPmax	Maximum setpoint
    num_ignore Number of ignored requests 
    R	         Number of requests from zones/systems
                weighted by importance
    SPtrim	Trim amount
    SPres	Respond amount
    SPres-max	Maximum response per time interval
    """
    
    def __init__(self, SPmin=None, SPmax=None, num_ignore=None, SPtrim=None, SPres=None, SPres_max=None):        
        self.SPmin = SPmin
        self.SPmax = SPmax
        self.num_ignore = num_ignore
        self.SPtrim = SPtrim
        self.SPres = SPres
        self.SPres_max = SPres_max
            
    def get_new_sp_clg(self, R, SP, verbose=False):
        """ R = number of requests, weighted by zone importance"""
        # calculate the response
        response = self.SPtrim + self.SPres * max(R - self.num_ignore,0.0)
        
        # limit the response per timestep to SPres_max
        response = self.SPres_max if abs(response) > \
                   abs(self.SPres_max) else response
        
        rv = SP + response
        # Ensure the setpoint stays within the desired range
        rv = self.SPmin if rv < self.SPmin else rv
        rv = self.SPmax if rv > self.SPmax else rv

        return rv
    
    def get_new_sp_htg(self, R, SP, verbose=False):
        """ R = number of requests, weighted by zone importance"""
        #calculate the response
        response = -self.SPtrim - self.SPres * max(R - self.num_ignore,0.0)
        
        # limit the response per timestep to SPres_max
        response = -self.SPres_max if abs(response) > \
                   abs(self.SPres_max) else response
        
        rv = SP + response
        # Ensure the setpoint stays up to 68F for heating requests
        rv = self.SPmin if rv < self.SPmin else rv
        rv = self.SPmax if rv > self.SPmax else rv

        return rv
