def day_of_week_int_to_str(day_of_week):
    kv = {0:"Monday",
          1:"Tuesday",
          2:"Wednesday",
          3: "Thursday",
          4: "Friday",
          5: "Saturday",
          6: "Sunday"
          }
    return kv[day_of_week]

def working_hour_str_to_num(hour_str):
    kv = {
        '6 AM':6,
        '7 AM':7,
        '8 AM':8,
        '9 AM':9,
        '10 AM':10,
        '11 AM':11,
        '12 PM':12,
        '1 PM':13,
        '2 PM':14,
        '3 PM':15,
        '4 PM':16,
        '5 PM':17,
        '6 PM':18,
        '7 PM':19,
        '8 PM':20,
        '9 PM':21,
        '10 PM':22,
        '11 PM':23,
        '12 AM':24
    }
    return kv[hour_str]

working_hours_list = ['6 AM','7 AM','8 AM','9 AM','10 AM','11 AM','12 PM','1 PM','2 PM','3 PM','4 PM','5 PM','6 PM','7 PM','8 PM','9 PM','10 PM','11 PM','12 AM']