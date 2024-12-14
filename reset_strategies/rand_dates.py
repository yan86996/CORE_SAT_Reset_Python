import datetime as dt
import numpy as np

rand_dates_Baseline = np.array([dt.date(2024, 11, 6),  dt.date(2024, 11, 8),
<<<<<<< HEAD
                       dt.date(2024, 11, 21),  dt.date(2024, 11, 30),                       
                       ])

rand_dates_G36 = np.array([dt.date(2024, 11, 23),   dt.date(2024, 12, 6),
                           dt.date(2024, 12, 9),   dt.date(2024, 12, 10),
                           dt.date(2024, 12, 12),  dt.date(2024, 12, 13),                           
                            ])
                       

rand_dates_CORE = np.array([dt.date(2024, 11, 20), dt.date(2024, 11, 21), 
                            dt.date(2024, 11, 22), dt.date(2024, 11, 23),   
                            dt.date(2024, 11, 25), dt.date(2024, 11, 26), 
                            dt.date(2024, 11, 27), dt.date(2024, 11, 28), 
                            dt.date(2024, 11, 29), dt.date(2024, 11, 30),
                            dt.date(2024, 12, 2),  dt.date(2024, 12, 3),
                            dt.date(2024, 12, 4),  dt.date(2024, 12, 5),
                            ])
=======
                                dt.date(2024, 11, 21),  dt.date(2024, 11, 30),                       
                               ])

rand_dates_G36 = np.array([dt.date(2024, 11, 23),   dt.date(2024, 12, 6),
                           dt.date(2024, 12, 7),   dt.date(2024, 12, 8),
                          ])                     

# TO CHANGE
start_date = dt.date(2024, 12, 9)
end_date = dt.date(2025, 1, 31)
# Generate continuous dates
num_days = (end_date - start_date).days + 1
rand_dates_CORE = np.array([start_date + dt.timedelta(days=i) for i in range(num_days)])
>>>>>>> effb00b (Initial commit)
                       
