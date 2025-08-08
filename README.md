# network_scanner
### Core Functions
1. &zwnj;**Smart Scanning**&zwnj;: Supports custom IP range scanning (e.g., 192.168.1.0/24), allowing setting of timed scans by seconds, specific intervals, or instant execution to detect LAN IP assets.
2. &zwnj;**Device Management**&zwnj;: Automatically identifies online devices, displaying key details like IP, MAC, hostname, and enables manual editing of user and department information.
3. &zwnj;**Time-based Query**&zwnj;: Automatically saves scheduled task results to a database, enabling queries of online/offline host assets by specific time periods.
4. &zwnj;**Data Export**&zwnj;: Supports exporting scan results to CSV format for reporting and analysis.

### Key Advantages
- &zwnj;**Visual Interface**&zwnj;: Intuitive design for ease of use
- &zwnj;**Real-time Monitoring**&zwnj;: Tracks device status changes instantly
- &zwnj;**Asset Association**&zwnj;: Department/user linking for better accountability

### Applicable Scenarios
- &zwnj;**Enterprise IT**&zwnj;: Efficient network oversight and maintenance
- &zwnj;**Troubleshooting**&zwnj;: Quick identification of network issues
- &zwnj;**Asset Tracking**&zwnj;: Lifecycle management of devices

## Command-Line Usage
The scanner supports three key parameters for customized network scanning:ml-citation{ref="2,8" data="citationList"}:

### Interval Timing (`-t/--interval`)
- Specify scan frequency in seconds (0 for single execution)  
- Example: `-t 300` for 5-minute recurring scans

### Output Control (`-o/--output`)
- Define CSV output path for scan results  
- Example: `-o 'scan_results.csv'` saves to current directory

### IP Exclusion (`-e/--exclude`)
- List IPs to skip during scanning (comma-separated)  
- Example: `-e '192.168.1.1,192.168.1.100'` excludes gateway and static IPs


## GUI Usage
The graphical interface (`lan_scanner_gui.py`) provides visual controls matching all command-line functionality:ml-citation{ref="10" data="citationList"}:
- IP range selector with CIDR notation support
- Real-time device list with MAC/IP/hostname details
- Scheduled scanning configuration panel
- Export buttons for CSV generation

## Technical Implementation
The tool utilizes ARP protocol for device discovery:ml-citation{ref="2" data="citationList"} and supports:
- Multi-threaded scanning for efficiency:ml-citation{ref="8,9" data="citationList"}
- Cross-platform compatibility (Windows/Linux/macOS)
- Minimal dependencies (Python standard library + scapy)

For advanced users, the scanner can be integrated with network monitoring systems through its CSV output format:ml-citation{ref="5" data="citationList"}.

## Best Practices
1. Avoid scanning during peak hours to minimize network impact:ml-citation{ref="5" data="citationList"}
2. Combine with `-e` parameter to exclude critical infrastructure:ml-citation{ref="11" data="citationList"}
3. Schedule regular scans for asset tracking (e.g., `-t 86400` for daily):ml-citation{ref="16" data="citationList"}  

The tool's architecture allows extension with additional network protocols and device fingerprinting capabilities.
