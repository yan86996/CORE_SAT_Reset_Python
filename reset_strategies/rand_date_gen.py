import datetime as dt
import numpy as np

# extracted by extract_dev_ID.py
rand_dates_Baseline = np.array([dt.date(2024, 11, 6),  dt.date(2024, 11, 8),
                       dt.date(2024, 11, 21),  dt.date(2024, 11, 30),                       
                       ])

rand_dates_G36 = np.array([dt.date(2024, 11, 23),   dt.date(2024, 12, 6),
                           dt.date(2024, 12, 9),   dt.date(2024, 12, 10),
                           dt.date(2024, 12, 12),  dt.date(2024, 12, 13),                           
                            ])

# TO CHANGE
start_date = dt.date(2025, 2, 1)
end_date = dt.date(2025, 3, 31)
# Generate continuous dates
num_days = (end_date - start_date).days + 1
rand_dates_CORE = np.array([start_date + dt.timedelta(days=i) for i in range(num_days)])
                       
