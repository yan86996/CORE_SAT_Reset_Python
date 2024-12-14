import numpy as np
import datetime
start = datetime.date(2016,7,27)
arr = np.array([start + datetime.timedelta(days=1*i) for i in xrange(600)])
np.random.shuffle(arr)
rand = arr[:300]
RAND_DATES = np.sort(rand)
#RAND_DATES = np.sort(np.append(rand, rand + datetime.timedelta(days=1)))
print RAND_DATES
