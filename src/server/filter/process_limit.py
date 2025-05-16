import time
from collections import OrderedDict

TIME_LIMIT = 3 # seconds
MAX_PROCESSES = 1000 # Max amount of processes

class ProcessDebouncer:
    def __init__(self, time_limit=TIME_LIMIT, max_processes=MAX_PROCESSES):
        self.time_limit : int = time_limit
        self.max_processes : int = max_processes
        self.cache : OrderedDict = OrderedDict()

    def should_log(self, process_name : str) -> bool:
        """
            Check if the process should be logged based on the time limit and max processes.

            INPUT: process_name
            OUTPUT: Wether the process should be logged or not

            @process_name: The name of the process to check
        """
        cur_time = time.time()
        
        if process_name in self.cache:
            last_time = self.cache[process_name]

            if cur_time - last_time < self.time_limit:
                return False
            
            # Signal that the process has been used
            # Therefore when we would remove processes to reduce weight
            # This process is unlikely to be removed
            self.cache.move_to_end(process_name)
        
        self.cache[process_name] = cur_time
        if len(self.cache) > self.max_processes:
            self.cache.popitem(last=False)
        
        return True