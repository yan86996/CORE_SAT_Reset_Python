from datetime import datetime, timedelta
import pdb

def price(datetime_obj, supply_voltage=2):
  """Return the energy charge ($/kWh) for date and time based on PG&E 
  tariffs

  Parameters
  ----------
  datetime_obj: datetime object
      datetime object of the date and time the energy charge need to be
      calculated for
  supply_voltage: int
      column indice of the supply voltage from low to high
      UC Berkeley is in the highest category, i.e. index 2
      default value for UC Berkeley: 2
  
  Returns
  -------
  price: float
    The energy charge ($/kWh) of the currrent time based on PG&E tariff

  """    
  # Define the price period based on PG&E schedule
  quarters = {1: {2024: 'q1', 2025: 'q1', 2026: 'q1'},
              2: {2024: 'q1', 2025: 'q1', 2026: 'q1'},
              3: {2024: 'q2', 2025: 'q2', 2026: 'q2'},
              4: {2024: 'q2', 2025: 'q2', 2026: 'q2'},
              5: {2024: 'q3', 2025: 'q2', 2026: 'q2'},
              6: {2024: 'q3', 2025: 'q2', 2026: 'q2'},
              7: {2024: 'q3', 2025: 'q2', 2026: 'q2'},# doubble check
              8: {2024: 'q3', 2025: 'q2', 2026: 'q2'},# double check
              9: {2024: 'q3', 2025: 'q2', 2026: 'q2'},# double check
              10: {2024: 'q4', 2025: 'q2', 2026: 'q2'},#double check
              11: {2024: 'q4', 2025: 'q2', 2026: 'q2'},# double check
              12: {2024: 'q4', 2025: 'q2', 2026: 'q2'}}

  # Season prices different in 2024 depending on the quarter
  # peak_summer['q3'][0] was not provided, used ratio from q4 secondary/primary
  #TODO: Update pricing for 2026  
  season_price = {2024:{
                        'q1':{'part_peak_winter':[0.0932, 0.0930, 0.08166],
                              'off_peak_winter': [0.07339, 0.07734, 0.06968]},
                        'q2':{'part_peak_winter':[0.09471, 0.09451, 0.08317],
                              'off_peak_winter': [0.07490, 0.07885, 0.07119]},
                        'q3':{'peak_summer': [0.14842, 0.14791, 0.1043],
                              'part_peak_summer': [0.10552, 0.10421, 0.08594],
                              'off_peak_summer': [0.07723, 0.07865, 0.07057]},
                        'q4':{'peak_summer': [0.15145, 0.15093, 0.10604],
                              'part_peak_summer': [0.10722, 0.1059, 0.08713],
                              'off_peak_summer': [0.07807, 0.07957, 0.07129],
                              'part_peak_winter': [0.10094,0.10081, 0.08855],
                              'off_peak_winter': [0.07925,0.08366, 0.07542]}},
                 2025:{
                       'q1':{'peak_summer':[0.15072, 0.15009, 0.10432],
                             'part_peak_summer':[0.10575, 0.10432, 0.0851],
                             'off_peak_summer': [0.07611, 0.07755, 0.069],
                             'part_peak_winter': [0.09936, 0.09914, 0.08654],
                             'off_peak_winter': [0.07731, 0.08171, 0.0732]},
                       'q2':{'peak_summer':[0.14772, 0.14709, 0.10132],
                             'part_peak_summer':[0.10275, 0.10132, 0.0821],
                             'off_peak_summer': [0.07311, 0.07455, 0.066],
                             'part_peak_winter': [0.09636, 0.09614, 0.08354],
                             'off_peak_winter': [0.07431, 0.07871, 0.0702]}},
                  2026:{
                        'q1': {'peak_summer':[0.13750, 0.13902, 0.09629],
                               'part_peak_summer':[0.10098, 0.09877, 0.08416],
                               'off_peak_summer':[0.07591, 0.07402, 0.06811],
                               'part_peak_winter':[0.09567, 0.09347, 0.08607],
                               'off_peak_winter':[0.08209, 0.08010, 0.07374]},
                        'q2': {'peak_summer':[0.13793,0.13945, 0.09672],
                               'part_peak_summer':[0.10141, 0.09920, 0.08459],
                               'off_peak_summer':[0.07634, 0.07445, 0.06854],
                               'part_peak_winter':[0.09610, 0.09390, 0.08650],
                               'off_peak_winter':[0.08252, 0.08053, 0.07417]}},
                  2017:{
                        'q1': {'peak_summer':[0.14423, 0.14572, 0.10259],
                               'part_peak_summer':[0.10738, 0.10510, 0.09036],
                               'off_peak_summer':[0.08208, 0.08012, 0.07417],
                               'part_peak_winter':[0.10203, 0.09975, 0.09228],
                               'off_peak_winter':[0.08832, 0.08626, 0.07985]},
                        'q2': {'peak_summer':[0.14423, 0.14572, 0.10259],
                               'part_peak_summer':[0.10738, 0.10510, 0.09036],
                               'off_peak_summer':[0.08208, 0.08012, 0.07417],
                               'part_peak_winter':[0.10203, 0.09975, 0.09228],
                               'off_peak_winter':[0.08832, 0.08626, 0.07985]}
                       }}
                      
#  peak_summer = {2024: [0.15145, 0.15093, 0.10604],
#                 2025: [0.15072, 0.15009, 0.10432],
#                 2026: []}
#  part_peak_summer = {2024: [0.10722, 0.10590, 0.08713],
#                      2025: [0.10575, 0.10432, 0.08510],  
#                      2026: []} 
#  off_peak_summer = {2024: [0.07807, 0.07957, 0.07129], 
#                     2025: [0.07611, 0.07755, 0.06900],
#                     2026: []} 
#  part_peak_winter = {2024: [0.10094, 0.10081, 0.08855], 
#                      2025: [0.09936, 0.09914, 0.08654],
#                      2026: [0.09936, 0.09914, 0.08654]} 
#  off_peak_winter =  {2024: [0.07925, 0.08366, 0.07542], 
#                      2025: [0.07731, 0.08171, 0.07320],
#                      2026: [0.07731, 0.08171, 0.07320]} 

  dt = datetime_obj

  # Assure the input date/time is anterior to the curent time
  assert dt < datetime.now(), "Input date should be anterior to the current date"
  if not dt.year in season_price.keys(): 
    raise Exception("Prices are only valid for %s\nDate entered is: %s"\
                    %(sorted(season_price.keys()),str(dt)))
  
  energy_charge = season_price[dt.year][quarters[dt.month][dt.year]]

  # Summer pricing apply May-October
  if dt.month >= 5 and dt.month <= 9:
    if (dt.hour > 8 or (dt.hour == 8 and dt.minute >= 30)) and \
		    (dt.hour < 21 or (dt.hour == 21 and dt.minute <30)):
      if dt.hour >= 12 and dt.hour < 18:
        price = energy_charge['peak_summer'][supply_voltage]
      else:
        price = energy_charge['part_peak_summer'][supply_voltage]
    else:
      price = energy_charge['off_peak_summer'][supply_voltage]

  # Winter pricing apply November-April
  else:
    if (dt.hour > 8 or (dt.hour == 8 and dt.minute >= 30)) and \
		    (dt.hour < 21 or (dt.hour == 21 and dt.minute <30)):
      price = energy_charge['part_peak_winter'][supply_voltage]
    else:
      price = energy_charge['off_peak_winter'][supply_voltage]
  return price

if __name__=='__main__':
  dt = datetime(2024,6,14,10)
  pr = price(dt)
  print ("""
        The electricity cost for transmission voltage customers 
        at 10am on June 14th 2024 was: $%f
        """%(pr))


