#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import math
from numpy.linalg import linalg
import copy

import helper as hp


class cstrafo():

    """ class to performe coordinate transformations """

    def __init__(self, zenith, azimuth, magnetic_field_vector=None, site=None):
        showeraxis = -1 * hp.spherical_to_cartesian(zenith, azimuth)  # -1 is because shower is propagating towards us
        if(magnetic_field_vector is None):
            magnetic_field_vector = hp.get_magnetic_field_vector(site=site)
        magnetic_field_normalized = magnetic_field_vector / linalg.norm(magnetic_field_vector)
        vxB = np.cross(showeraxis, magnetic_field_normalized)
        e1 = vxB
        e2 = np.cross(showeraxis, vxB)
        e3 = np.cross(e1, e2)
        e1 /= linalg.norm(e1)
        e2 /= linalg.norm(e2)
        e3 /= linalg.norm(e3)
        self.__transformation_matrix_vBvvB = copy.copy(np.matrix([e1, e2, e3]))
        self.__inverse_transformation_matrix_vBvvB = np.linalg.inv(self.__transformation_matrix_vBvvB)

        # initilize transformation matrix to on-sky coordinate system (etheta, ephi, er)
        ct = np.cos(zenith)
        st = np.sin(zenith)
        cp = np.cos(azimuth)
        sp = np.sin(azimuth)
        e1 = np.array([st * cp, st * sp, ct])
        e2 = np.array([ct * cp, ct * sp, -st])
        e3 = np.array([-sp, cp, 0])
        self.__transformation_matrix_onsky = np.matrix([e1, e2, e3])
        self.__inverse_transformation_matrix_onsky = np.linalg.inv(self.__transformation_matrix_onsky)

        # initilize transformation matrix from magnetic north to geographic north coordinate system
        declination = hp.get_declination(magnetic_field_vector)
        c = np.cos(-1 * declination)
        s = np.sin(-1 * declination)
        e1 = np.array([c, -s, 0])
        e2 = np.array([s, c, 0])
        e3 = np.array([0, 0, 1])
        self.__transformation_matrix_magnetic = np.matrix([e1, e2, e3])
        self.__inverse_transformation_matrix_magnetic = np.linalg.inv(self.__transformation_matrix_magnetic)

    def __transform(self, positions, matrix):
        if(len(positions.shape) == 1):
            temp = np.squeeze(np.asarray(np.dot(matrix, positions)))
            return temp
        else:
            result = np.zeros_like(positions)
            for i, pos in enumerate(positions):
                temp = np.squeeze(np.asarray(np.dot(matrix, pos)))
                result[i] = temp
            return result

    def transform_from_ground_to_onsky(self, positions):
        return self.__transform(positions, self.__transformation_matrix_onsky)

    def transform_from_onsky_to_ground(self, positions):
        return self.__transform(positions, self.__inverse_transformation_matrix_onsky)

    def transform_from_magnetic_to_geographic(self, positions):
        return self.__transform(positions, self.__transformation_matrix_magnetic)

    def transform_from_geographic_to_magnetic(self, positions):
        return self.__transform(positions, self.__inverse_transformation_matrix_magnetic)

    def transform_to_vxB_vxvxB(self, station_position, core=None):
        """ transform a single station position or a list of multiple
        station positions into vxB, vxvxB shower plane """
        if(core is not None):
            station_position = np.array(copy.deepcopy(station_position))
        if(len(station_position.shape) == 1):
            if(core is not None):
                station_position -= core
            return np.squeeze(np.asarray(np.dot(self.__transformation_matrix_vBvvB, station_position)))
        else:
            result = []
            for pos in station_position:
                if(core is not None):
                    pos -= core
                result.append(np.squeeze(np.asarray(np.dot(self.__transformation_matrix_vBvvB, pos))))
            return np.array(result)

    def transform_from_vxB_vxvxB(self, station_position, core=None):
        """ transform a single station position or a list of multiple
        station positions back to x,y,z CS """
        if(core is not None):
            station_position = copy.deepcopy(station_position)
        if(len(station_position.shape) == 1):
            temp = np.squeeze(np.asarray(np.dot(self.__inverse_transformation_matrix_vBvvB, station_position)))
            if(core is not None):
                return temp + core
            return temp
        else:
            result = []
            for pos in station_position:
                temp = np.squeeze(np.asarray(np.dot(self.__inverse_transformation_matrix_vBvvB, pos)))
                if(core is not None):
                    result.append(temp + core)
                else:
                    result.append(temp)
            return np.array(result)

    def transform_from_vxB_vxvxB_2D(self, station_position, core=None):
        """ transform a single station position or a list of multiple
        station positions back to x,y,z CS """
        if(core is not None):
            station_position = copy.deepcopy(station_position)
        if(len(station_position.shape) == 1):
            position = np.array([station_position[0], station_position[1],
                                 self.get_height_in_showerplane(station_position[0], station_position[1])])
            result = np.squeeze(np.asarray(np.dot(self.__inverse_transformation_matrix_vBvvB, position)))
            if(core is not None):
                result += core
            return result
        else:
            result = []
            for pos in station_position:
                position = np.array([pos[0], pos[1], self.get_height_in_showerplane(pos[0], pos[1])])
                pos_transformed = np.squeeze(np.asarray(np.dot(self.__inverse_transformation_matrix_vBvvB, position)))
                if(core is not None):
                    pos_transformed += core
                result.append(pos_transformed)
            return np.array(result)

    def get_height_in_showerplane(self, x, y):
        return -1. * (self.__transformation_matrix_vBvvB[0, 2] * x + self.__transformation_matrix_vBvvB[1, 2] * y) / self.__transformation_matrix_vBvvB[2, 2]

    def get_euler_angles(self):
        R = self.__transformation_matrix_vBvvB
        if(abs(R[2, 0]) != 1):
            theta_1 = -math.asin(R[2, 0])
            theta_2 = math.pi - theta_1
            psi_1 = math.atan2(R[2, 1] / math.cos(theta_1), R[2, 2] / math.cos(theta_1))
            psi_2 = math.atan2(R[2, 1] / math.cos(theta_2), R[2, 2] / math.cos(theta_2))
            phi_1 = math.atan2(R[1, 0] / math.cos(theta_1), R[0, 0] / math.cos(theta_1))
            phi_2 = math.atan2(R[1, 0] / math.cos(theta_2), R[0, 0] / math.cos(theta_2))
        else:
            phi_1 = 0.
            if(R[2, 0] == -1):
                theta_1 = math.pi * 0.5
                psi_1 = phi_1 + math.atan2(R[0, 1], R[0, 2])
            else:
                theta_1 = -1. * math.pi * 0.5
                psi_1 = -phi_1 + math.atan2(-R[0, 1], -R[0, 2])
        return psi_1, theta_1, phi_1


if __name__ == "__main__":
    zenith = np.deg2rad(21.2149)
    azimuth = np.deg2rad(-143.746 + 360.)
    cs = cstrafo(zenith, azimuth)
    print [-29.2463, 36.3054, 2.73222], cs.transform_to_vxB_vxvxB(np.array([-29.2463, 36.3054, 2.73222]))
    print [-288.319, -100.42, 5.16209], cs.transform_to_vxB_vxvxB(np.array([-288.319, -100.42, 5.16209]))

