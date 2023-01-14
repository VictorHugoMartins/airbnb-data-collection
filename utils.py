import psycopg2.errorcodes
from geopy import distance

def get_area_coordinates_from_db(config, area):
    conn = config.connect()
    cur = conn.cursor()

    sql = """SELECT bb_n_lat, bb_s_lat, bb_w_lng, bb_e_lng
            from search_area
            where name = %s
            limit 1""" # os q precisa atualizar
    cur.execute(sql, (area,))                
    result = cur.fetchall()

    lat_max = float(result[0][0])
    lat_min = float(result[0][1])
    lng_min = float(result[0][2])
    lng_max = float(result[0][3])

    return (lat_max, lat_min, lng_max, lng_min)

def is_inside(lat_center, lng_center, lat_test, lng_test):
    center_point = [{'lat': lat_center, 'lng': lng_center}]
    test_point = [{'lat': lat_test, 'lng': lng_test}]

    for radius in range(50):
        center_point_tuple = tuple(center_point[0].values()) # (-7.7940023, 110.3656535)
        test_point_tuple = tuple(test_point[0].values()) # (-7.79457, 110.36563)

        dis = distance.distance(center_point_tuple, test_point_tuple).km
        
        if dis <= radius:
            print("{} point is inside the {} km radius from {} coordinate".\
                    format(test_point_tuple, radius/1000, center_point_tuple))
            return True
    return False