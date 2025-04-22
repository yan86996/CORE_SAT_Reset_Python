from datetime import datetime, timedelta

def electricity_price(datetime_obj):
    # Define the price period based on PG&E schedule
    month_rate = {1: {2025: 0.081,},  2: {2025: 0.066,},  3: {2025: 0.074,},
                  4: {2025: 0.069,},  5: {2025: 0.074,},  6: {2025: 0.119,},
                  7: {2025: 0.127,},  8: {2025: 0.124,},  9: {2025: 0.136,},
                 10: {2025: 0.106,}, 11: {2025: 0.075,}, 12: {2025: 1.013,},
                 }
     
    dt = datetime_obj
    energy_charge = month_rate[dt.month][dt.year]
    
    return energy_charge

def steam_price(datetime_obj):
    # Define the price period based on PG&E schedule
    month_rate = {1: {2025: 51.972/1000,},  2: {2025: 51.972/1000,},  3: {2025: 51.972/1000,},
                  4: {2025: 51.972/1000,},  5: {2025: 51.972/1000,},  6: {2025: 51.972/1000,},
                  7: {2025: 51.972/1000,},  8: {2025: 51.972/1000,},  9: {2025: 51.972/1000,},
                 10: {2025: 51.972/1000,}, 11: {2025: 51.972/1000,}, 12: {2025: 51.972/1000,},
                 }
     
    dt = datetime_obj
    energy_charge = month_rate[dt.month][dt.year]
    
    return energy_charge


if __name__=='__main__':
    dt = datetime.now()
    elec_pr = electricity_price(dt)
    steam_pr = steam_price(dt)
    
    print ("""
          The electricity cost now is: $%f
          """%(elec_pr))
          
    print ("""
          The steam cost now is: $%f
          """%(steam_pr))
