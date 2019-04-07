from tes import TES
from QET import QET
import numpy as np

class Detector:

    def __init__(self, name, fridge, absorber, n_channel, n_TES=1185,
                 l_TES=140e-6, l_fin=200e-6, h_fin=600e-6, l_overlap=10e-6,
                 w_rail_main=8e-6, w_rail_qet=4e-6):
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

        resistivity = 10
        n_fin = 6

        self._TES = TES(40e-9, l_TES, 3.5e-6, 1, n_fin, resistivity)
        self._QET = QET(n_fin, l_fin, h_fin, l_overlap, self._TES)

        # -------------- TES -------------
        # Resistance of N_TES sensors in parallel.
        self._total_TES_R = self._TES.get_R() / self._N_TES

        # Total volume of Tungsten
        self._total_TES_vol = self._TES.get_volume()

        # ------------- QET Fins -----------------
        # Percentage of surface area covered by QET Fins
        self._SA_active = self._n_channel * n_TES * self._QET.get_a_fin()

        # Average area per cell, and corresponding length
        a_cell = self._absorber.get_pattern_SA() / (n_channel * n_TES) # 1/2 channels on each side
        self._l_cell = np.sqrt(a_cell)

        y_cell = 2 * QET.get_l_fin() + TES.get_L()

        if self._l_cell > y_cell:
            # Design is not close packed. Get passive Al/QET
            a_passive_qet = self._l_cell * w_rail_main + (self._l_cell - y_cell) * w_rail_qet

        else:
            # Design is close packed. No vertical rail to QET
            x_cell = a_cell / y_cell
            a_passive_qet = x_cell * w_rail_main

        tes_passive = a_passive_qet * n_channel * n_TES
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
        # TODO Get phonon absorption time tau for PD2 by running matlab script. No need to simulate from iZIP again
        self._t_pabsb = 100;

        self._w_collect = 1/self._t_pabsb

        # ------------ Total Phonon Collection Efficiency -------------

        # The loss mechanisms in our detector are:
        # 1) subgap downconversion of athermal phonons in the crystal
        # 2) collection of athermal phonons by passive metal on the surface of our detector ( Det.ePcollect)
        # 3) Efficiency of QP production in Al fin (QET.ePQP)
        # 4) Efficiency of QP transport to TES (QET.eQPabsb)
        # 5) Energy conversion efficiency at W/Al interface
        # 6) ?

        # Let's combine 1), 5), and 6) together and assume that it is the same as the measured/derived value from iZIP4
        self._e156 = 100 # TODO Get iZIP combined efficiency.

        # Total collection efficiency:
        self._eEabsb = self._e156 * self._ePcollect # TODO QET.ePQP implement and get QP transport efficiency in QET
                                                    # TODO by getting explanation of lines 193-197.

        # ------------ Thermal Conductance to Bath ---------------
        self._kpb = 1.55e-4
        # Thermal conductance coefficient between detector and bath
        self._nkpb = 4

        # ----------- Electronics ----------
        # TODO Get total inductance by interacting with electronics class



    def get_energy_resolution(self):
        pass

    def get_position_resolution(self):
        pass




