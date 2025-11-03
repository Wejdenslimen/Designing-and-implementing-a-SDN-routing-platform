from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.link import TCLink
from mininet.log import setLogLevel, info

class Topo(Topo):
    def build(self):
        # Hosts
        h1 = self.addHost('h1', ip='192.168.1.1/24', mac='00:00:00:00:00:01')
        h2 = self.addHost('h2', ip='192.168.1.2/24', mac='00:00:00:00:00:02')
        h3 = self.addHost('h3', ip='192.168.1.3/24', mac='00:00:00:00:00:03')
        h4 = self.addHost('h4', ip='192.168.1.4/24', mac='00:00:00:00:00:04')
        h5 = self.addHost('h5', ip='192.168.1.5/24', mac='00:00:00:00:00:05')
        h6 = self.addHost('h6', ip='192.168.1.6/24', mac='00:00:00:00:00:06')
        h7 = self.addHost('h7', ip='192.168.1.7/24', mac='00:00:00:00:00:07')
        h8 = self.addHost('h8', ip='192.168.1.8/24', mac='00:00:00:00:00:08')

        # Switches d’accès/distribution
        s1 = self.addSwitch('s1', dpid='0000000000000001', protocols='OpenFlow13')
        s2 = self.addSwitch('s2', dpid='0000000000000002', protocols='OpenFlow13')
        s3 = self.addSwitch('s3', dpid='0000000000000003', protocols='OpenFlow13')
        s4 = self.addSwitch('s4', dpid='0000000000000004', protocols='OpenFlow13')

        # Switches cœur
        s6 = self.addSwitch('s6', dpid='0000000000000006', protocols='OpenFlow13')
        s7 = self.addSwitch('s7', dpid='0000000000000007', protocols='OpenFlow13')
        s8 = self.addSwitch('s8', dpid='0000000000000008', protocols='OpenFlow13')

        # Connexions hôtes <-> switches d'accès
        self.addLink(h1, s1)
        self.addLink(h2, s1)

        self.addLink(h3, s2)
        self.addLink(h4, s2)

        self.addLink(h5, s3)
        self.addLink(h6, s3)

        self.addLink(h7, s4)
        self.addLink(h8, s4)

        # Connexions accès -> cœur
        self.addLink(s1, s6)
        self.addLink(s1, s7)
        self.addLink(s1, s8)

        self.addLink(s2, s7)
        self.addLink(s2, s8)

        self.addLink(s3, s6)
        self.addLink(s3, s7)
        self.addLink(s3, s8)

        self.addLink(s4, s6)
        self.addLink(s4, s7)
        self.addLink(s4, s8)

        # Connexions cœur -> cœur (maillage complet)
        self.addLink(s6, s7)
        self.addLink(s6, s8)
        self.addLink(s7, s8)

topos = {'matopo': (lambda: Topo())}
