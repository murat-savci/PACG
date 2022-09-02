import numpy as np

def goci_sensor_zenith(latitude, longitude):
    GEOSTATIONARY_ORBIT_ALTITUDE_KM = 35786.0
    EARTH_RADIUS_KM = 6371.0
    GOCI_ORBIT_LONGITUDE = 128.2
    longdiffr = np.deg2rad(longitude - GOCI_ORBIT_LONGITUDE)
    eslatr = np.deg2rad(latitude)
    r1 = 1.0 + GEOSTATIONARY_ORBIT_ALTITUDE_KM / EARTH_RADIUS_KM
    v1 = r1 * np.cos(eslatr) * np.cos(longdiffr) - 1.0
    v2 = r1 * np.sqrt(1 - np.cos(eslatr) * np.cos(eslatr) *
                        np.cos(longdiffr) * np.cos(longdiffr))
    eselevation = np.rad2deg(np.arctan(v1 / v2))
    eselrefracted = eselevation
    eselrefracted[eselevation < 30.0] = (eselevation[eselevation < 30.0] + np.sqrt(
        np.power(eselevation[eselevation < 30.0], 2) + 4.132)) / 2.0
    m_satellite_zenith_angle_degree = 90.0 - eselrefracted
    return m_satellite_zenith_angle_degree

def goci_sensor_azimuth(latitude, longitude, satellite_longitude):
    longdiffr_rad = np.deg2rad(longitude - satellite_longitude)
    esazimuth_deg = 180.0 + \
        np.rad2deg(np.arctan(np.tan(longdiffr_rad) /
                                np.sin(np.deg2rad(latitude))))
    esazimuth_deg[latitude < 0.0] = esazimuth_deg[latitude < 0.0] - 180.0
    esazimuth_deg[esazimuth_deg <
                    0.0] = esazimuth_deg[esazimuth_deg < 0.0] + 360.0
    return esazimuth_deg

def goci_slots(nav_data, height, width, band):
    PARAM_INDEX_A = 5
    PARAM_INDEX_B = 14
    PARAM_INDEX_C = 22
    PARAM_INDEX_D = 31
    di = np.full([height, width, 16], float('-inf'))

    for slot_index in range(16):
        y, x = np.mgrid[0:height, 0:width]
        sbp = nav_data[band * 16 + slot_index]
        sbp = np.hstack((sbp[4], sbp[5], sbp[6], sbp[7],
                        sbp[13][:9], sbp[15][:8], sbp[17][:9], sbp[19][:8]))

        x = (x - sbp[0]) / sbp[2]
        y = (y - sbp[1]) / sbp[3]

        xs = np.power(x, 2)
        ys = np.power(y, 2)

        matrix = np.array([x, y, np.multiply(x, y), xs, ys, np.multiply(xs, y),
                            np.multiply(x, ys), np.multiply(xs, ys)])

        del x, y, xs, ys

        P1 = np.full((height, width), sbp[PARAM_INDEX_A - 1])
        P3 = np.full((height, width), sbp[PARAM_INDEX_C - 1])
        P2 = np.full((height, width), 1.0)
        P4 = np.full((height, width), 1.0)

        for param_index in range(8):
            P1 += matrix[param_index] * sbp[PARAM_INDEX_A + param_index]
            P3 += matrix[param_index] * sbp[PARAM_INDEX_C + param_index]
            P2 += matrix[param_index] * \
                sbp[PARAM_INDEX_B + param_index - 1]
            P4 += matrix[param_index] * \
                sbp[PARAM_INDEX_D + param_index - 1]

        del matrix, sbp

        xn = P1 / P2
        yn = P3 / P4

        del P1, P2, P3, P4

        valid = (np.abs(xn) <= 1.0) & (np.abs(yn) <= 1.0)
        di[valid, slot_index] = np.minimum(np.minimum(1.0 - xn[valid], 1.0 + xn[valid]),
                                            np.minimum(1.0 - yn[valid], 1.0 + yn[valid]))

        print("\tFinished slot", slot_index)

    slots = np.argmax(di, axis=2) + 1
    slots[np.amax(di, axis=2) == float('-inf')] = -1
    return slots

def goci_slots_time(nav_data):
    rel_time = np.zeros(16)
    for slot_index in range(16):
        for band_index in range(8):
            rel_time[slot_index] += nav_data[band_index * 16 + slot_index][2]

    rel_time /= 8
    return rel_time

def es_dist(year, day, sec):
    jd = 367*year - 7*(year+10/12)/4 + 275*1/9 + day + 1721014
    t = jd - 2451545.0+(sec-43200)/86400
    gs = 357.52772+0.9856002831*t
    esdist = 1.00014-0.01671 * \
        np.cos(np.deg2rad(gs))-0.00014*np.cos(np.deg2rad(2*gs))
    return np.power((1/esdist), 2)