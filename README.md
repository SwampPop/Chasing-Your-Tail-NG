# Chasing Your Tail-NG

A Wi-Fi probe request analyzer that helps track and analyze wireless devices in your area to help you determine if you're being followed. Built with Python, it integrates with Kismet for packet capture and WiGLE for SSID geolocation. 

## Features

- Real-time monitoring of Wi-Fi probe requests
- Time-window based device tracking (5, 10, 15, and 20 minute windows)
- WiGLE API integration for SSID location lookups
- MAC address and SSID filtering via ignore lists
- GUI interface for easy operation
- Detailed logging and analysis

## Requirements

- Python 3.6+
- Kismet
- Wi-Fi adapter supporting monitor mode
- Linux-based system
- WiGLE API key (optional)

## Quick Start

1. Install dependencies:
```
pip3 install -r requirements.txt
```

2. Configure `config.json` with your paths and settings
3. Launch the GUI:
```
python3 cyt_gui.py
```

4. Use GUI buttons to:
   - Check monitor mode status
   - Create/delete ignore lists
   - Start monitoring

## Command Line Usage

Start monitoring:
```
python3 chasing_your_tail.py
```

Analyze collected data:
```
python3 probe_analyzer.py [--local]
```

## Configuration

Edit `config.json` to set:
- Log file locations
- Time windows for tracking
- WiGLE API key
- Geographic search boundaries

## Videos 
- <a href="https://www.youtube.com/watch?v=1SmpgkE67Hc" target="_blank">https://www.youtube.com/watch?v=1SmpgkE67Hc</a>
- <a href="https://www.youtube.com/watch?v=YRZq4PoaWeU" target="_blank">https://www.youtube.com/watch?v=YRZq4PoaWeU</a>
- <a href="https://www.youtube.com/watch?v=nzCiOFJxbz4" target="_blank">https://www.youtube.com/watch?v=nzCiOFJxbz4</a>
- <a href="https://www.youtube.com/watch?v=7nSFcdZ2TBo" target="_blank">https://www.youtube.com/watch?v=7nSFcdZ2TBo</a>

## Author

@matt0177

## Thanks
Kismet for being amazing
@Singe for the same reason

## License

MIT License
