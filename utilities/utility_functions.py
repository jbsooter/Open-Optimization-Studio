import pandas as pd


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

time_increments_list = ['15 min','30 min','45 min','1 hr','1.25 hrs','1.5 hrs','1.75 hrs','2 hrs','2.25 hrs','2.5 hrs','2.75 hrs','3 hrs','3.25 hrs','3.5 hrs','3.75 hrs','4 hrs','4.25 hrs','4.5 hrs','4.75 hrs','5 hrs']

def time_increment_to_num_periods(time_increment):
    kv= {'15 min':1,
         '30 min':2,
         '45 min':3,
         '1 hr':4,
         '1.25 hrs':5,
         '1.5 hrs':6,
         '1.75 hrs':7,
         '2 hrs':8,
         '2.25 hrs':9,
         '2.5 hrs':10,
         '2.75 hrs':11,
         '3 hrs':12,
         '3.25 hrs':13,
         '3.5 hrs':14,
         '3.75 hrs':15,
         '4 hrs': 16,
         '4.25 hrs':17,
         '4.5 hrs':18,
         '4.75 hrs':19,
         '5 hrs':20
         }
    return kv[time_increment]

def decode_polyline(polyline, is3d=False):
    """Decodes a Polyline string into a GeoJSON geometry.
    :param polyline: An encoded polyline, only the geometry.
    :type polyline: string
    :param is3d: Specifies if geometry contains Z component.
    :type is3d: boolean
    :returns: GeoJSON Linestring geometry
    :rtype: dict
    """
    points = []
    index = lat = lng = z = 0

    while index < len(polyline):
        result = 1
        shift = 0
        while True:
            b = ord(polyline[index]) - 63 - 1
            index += 1
            result += b << shift
            shift += 5
            if b < 0x1F:
                break
        lat += (~result >> 1) if (result & 1) != 0 else (result >> 1)

        result = 1
        shift = 0
        while True:
            b = ord(polyline[index]) - 63 - 1
            index += 1
            result += b << shift
            shift += 5
            if b < 0x1F:
                break
        lng += ~(result >> 1) if (result & 1) != 0 else (result >> 1)

        if is3d:
            result = 1
            shift = 0
            while True:
                b = ord(polyline[index]) - 63 - 1
                index += 1
                result += b << shift
                shift += 5
                if b < 0x1F:
                    break
            if (result & 1) != 0:
                z += ~(result >> 1)
            else:
                z += result >> 1

            points.append(
                [
                    round(lng * 1e-5, 6),
                    round(lat * 1e-5, 6),
                    round(z * 1e-2, 1),
                ]
            )

        else:
            points.append([round(lng * 1e-5, 6), round(lat * 1e-5, 6)])

    #return coordinates for leaflet in Lat, Lon format
    coords = []
    for x in points:
        coords.append([x[1],x[0]])
    return coords