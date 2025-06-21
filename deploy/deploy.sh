#!/bin/bash
cp ./nodeAgent /usr/local/bin/
cp ./snb-node-agent.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable snb-node-agent
systemctl start snb-node-agent