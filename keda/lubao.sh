echo "nvidia" |
sudo -S tcpdump -i eth0 host 192.168.1.201 -w lidar.pcap
