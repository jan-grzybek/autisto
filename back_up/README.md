## Setting up back-up routine
First install MEGAcmd from https://mega.nz/cmd

Then run:
```
sudo bash ./set.sh
sudo crontab -e  # set cron to your preference, e.g. '30 * * * * /root/create_back_up.sh'
sudo mega-sync /root/back_ups /autisto_back_ups
```
