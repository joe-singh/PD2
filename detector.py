from tes import TES
from QET import QET
from MaterialProperties import TESMaterial
from electronics import Electronics
import numpy as np
import sys

k_b = 1.38e-3 # J/K
class Detector:

    def __init__(self, name, fridge, electronics, absorber, n_channel, n_TES=1185,
                 l_TES=140e-6, l_fin=200e-6, h_fin=600e-9, l_overlap=10e-6,
                 w_rail_main=6e-6, w_rail_qet=3e-6):
        """
        
        PD2 Detector Object
        
        :param name: Detector Name
        :param fridge: Fridge in which detector is in
        :param absorber: Absorbing part of detector
        :param n_channel: Number of channels
        :param N_TES: Number of TES on detector
        :param l_TES: Length of TES
        :param l_fin: Length of QET Fin
        :param h_fin: Height of QET Fin
        :param l_overlap: Length of ??
        """

        self._name = name
        self._fridge = fridge
        self._absorber = absorber
        self._n_channel = n_channel
        self._l_TES = l_TES
        self._l_fin = l_fin
        self._h_fin = h_fin
        self._l_overlap = l_overlap
        self._N_TES = n_TES
        self._w_rail_main = w_rail_main
        self._w_rail_qet = w_rail_qet
        self._electronics = electronics #Electronics(fridge, 5e-3, 6e-3, 75e-9, 25e-9, 6e-12) # SNOLAB values by default
        self._sigma_energy = 0

        resistivity = 9.6e-8 # Ohm m

        if l_fin > 100e-6:
            n_fin = 6
        else:
            n_fin = 4

        tungsten = TESMaterial()
        # True flag here because specifying resistance to be 300e-3 so that l_tes and n_tes are constrained.
        self._TES = TES(40e-9, l_TES, 3.5e-6, 1, n_fin, resistivity,
                        tungsten.get_gPep_v(), 5, -100, 1185, True)

        self._N_TES = self._TES.get_ntes()

        self._QET = QET(n_fin, l_fin, h_fin, l_overlap, self._TES)

        self._QET.set_qpabsb_eff(l_fin, h_fin, l_overlap, l_TES)

        # -------------- TES -------------
        # Resistance of N_TES sensors in parallel.
        self._total_TES_R = self._TES.get_R() / self._N_TES

        # Total volume of Tungsten
        self._total_TES_vol = self._TES.get_volume()

        # ------------- QET Fins -----------------
        # Percentage of surface area covered by QET Fins
        self._SA_active = self._n_channel * self._N_TES * self._QET.get_a_fin()

        # Average area per cell, and corresponding length
        a_cell = self._absorber.get_pattern_SA() / (n_channel * self._N_TES) # 1/2 channels on each side
        self._l_cell = np.sqrt(a_cell)

        y_cell = 2 * self._QET.get_l_fin() + self._TES.get_L()

        if self._l_cell > y_cell:
            # Design is not close packed. Get passive Al/QET
            a_passive_qet = self._l_cell * w_rail_main + (self._l_cell - y_cell) * w_rail_qet

        else:
            # Design is close packed. No vertical rail to QET
            x_cell = a_cell / y_cell
            a_passive_qet = x_cell * w_rail_main

        tes_passive = a_passive_qet * n_channel * self._N_TES
        outer_ring = 2 * np.pi * (self._absorber.get_R() - self._absorber.get_w_safety()) * w_rail_main
        inner_ring = outer_ring / (np.sqrt(2))
        inner_vertical_rail = 3 * (self._absorber.get_R() - self._absorber.get_w_safety()) * w_rail_main * (1 - np.sqrt(2)/2.0)
        outer_vertical_rail = (self._absorber.get_R() - self._absorber.get_w_safety()) * w_rail_main * (1 + np.sqrt(2)/2.0)

        # Total Passive Surface Area
        # 1. TES Passive Area
        # 2. Outer Ring
        # 3. Inner Ring
        # 4. Inner Vertical Rail
        # 5. Outer Vertical Rail
        self._SA_passive = tes_passive + outer_ring + inner_ring + inner_vertical_rail + outer_vertical_rail

        # Fraction of surface area which has phonon absorbing aluminum
        self._fSA_qpabsorb = (self._SA_passive + self._SA_active) / self._absorber.get_SA()

        # Fraction of Al which is QET fin which can produce signal
        self._ePcollect = self._SA_active / (self._SA_active + self._SA_passive)

        # ------------ Ballistic Phonon Absorption Time --------------
        if self._absorber.get_name() == 'Ge':
            self._t_pabsb = 750e-6 # TODO SET THIS PROPERLY
        elif self._absorber.get_name() == 'Si':
            self._t_pabsb = 1.7927e-05
        else:
            print("Incorrect Material. must be Ge or Si")
            sys.exit(1)

        PD2_absb_time = 20e-6
        absb_lscat = absorber.scattering_length()
        PD2_fSA_qpabsb = 0.0071453736535236241
        PD2_lscat = 0.001948849104859335


        self._t_pabsb = PD2_absb_time * (absb_lscat / PD2_lscat) * (PD2_fSA_qpabsb / self._fSA_qpabsorb)

        self._w_collect = 1/self._t_pabsb

        # ------------ Total Phonon Collection Efficiency -------------

        # The loss mechanisms in our detector are:
        # 1) subgap downconversion of athermal phonons in the crystal
        # 2) collection of athermal phonons by passive metal on the surface of our detector ( Det.ePcollect)
        # 3) Efficiency of QP production in Al fin (QET.ePQP)
        # 4) Efficiency of QP transport to TES (QET.eQPabsb)
        # 5) Energy conversion efficiency at W/Al interface
        # 6) ?

        # Phonon Downconversion Factor
        self._e_downconvert = 1/4000

        # Let's combine 1), 5), and 6) together and assume that it is the same as the measured/derived value from iZIP4
        self._e156 = 0.8690

        # Total collection efficiency:
        self._eEabsb = self._e156 * self._ePcollect * self._QET.get_eqpabsb() * self._QET.get_epqp() # * self._e_downconvert * self._fSA_qpabsorb 

        # ------------ Thermal Conductance to Bath ---------------
        self._kpb = 1.55e-4
        # Thermal conductance coefficient between detector and bath
        self._nkpb = 4

        # ----------- Electronics ----------
        self._total_L = self._electronics.get_l_squid() + self._electronics.get_l_p() + self._TES.get_L()

        # ---------- Response Variables to Be Set in Simulation of Noise ---------------
        self._response_omega = 0
        self._response_dPtdE = 0
        self._response_dIdP = 0
        self._response_z_tes = 0
        self._response_z_tot = 0
        self._response_dIdV = 0
        self._response_dIdV0 = 0
        self._response_dIdV_step = 0
        self._response_t = 0

        """
        print("---------------- DETECTOR PARAMETERS ----------------")
        print("nP %s" % self._n_channel)
        print("SAactive %s" % self._SA_active)
        print("lcell %s" % self._l_cell)
        print("SApassive %s" % self._SA_passive)
        print("fSA_QPabsb %s" % self._fSA_qpabsorb)
        print("ePcollect %s" % self._ePcollect)
        print("tau_pabsb %s" % self._t_pabsb)
        print("w_pabsb %s" % (1/self._t_pabsb))
        print("eE156 %s" % self._e156)
        print("eEabsb %s" % self._eEabsb)
        print("Kpb %s" % self._kpb)
        print("nKpb %s" % self._nkpb)
        print("------------------------------------------------\n")
        """

    def get_position_resolution(self):
        pass


    def get_TES(self):
        return self._TES

    def get_QET(self):
        return self._QET

    def get_fridge(self):
        return self._fridge

    def get_eEabsb(self):
        return self._eEabsb

    def get_collection_bandwidth(self):
        return self._w_collect

    def get_electronics(self):
        return self._electronics

    def set_response_omega(self, omega):
        self._response_omega = omega

    def get_response_omega(self):
        return self._response_omega

    def set_dPtdE(self, val):
        self._response_dPtdE = val

    def get_dPtdE(self):
        return self._response_dPtdE

    def set_dIdP(self, val):
        self._response_dIdP = val

    def get_dIdP(self):
        return self._response_dIdP

    def set_ztes(self, val):
        self._response_z_tes = val

    def set_ztot(self, val):
        self._response_z_tot = val

    def set_dIdV(self, val):
        self._response_dIdV = val

    def get_dIdV(self):
        return self._response_dIdV

    def set_dIdV0(self, val):
        self._response_dIdV0 = val

    def set_dIdV_step(self, val):
        self._response_dIdV_step = val

    def set_t(self, val):
        self._response_t = val

    def get_n_channel(self):
        return self._n_channel