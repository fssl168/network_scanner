import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path='lan_scanner.db'):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self._init_db()

    def _init_db(self):
        """初始化数据库连接和创建表"""
        # 确保数据库目录存在
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)

        # 连接数据库
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

        # 创建扫描结果表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS scan_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_time TIMESTAMP NOT NULL,
            hostname TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            mac_address TEXT NOT NULL,
            local_ip TEXT NOT NULL,
            network_range TEXT NOT NULL
        )
        ''')

        # 添加status列（如果不存在）
        try:
            self.cursor.execute('ALTER TABLE scan_results ADD COLUMN status TEXT')
        except sqlite3.OperationalError:
            pass  # 列已存在，忽略错误

        # 创建资产信息表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS asset_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mac_address TEXT NOT NULL,
            user_name TEXT,
            department TEXT,
            registration_time TIMESTAMP NOT NULL,
            notes TEXT,
            FOREIGN KEY (mac_address) REFERENCES scan_results(mac_address)
        )
        ''')

        # 创建索引以提高查询性能
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_scan_time ON scan_results (scan_time)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_ip_address ON scan_results (ip_address)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_mac_asset ON asset_info (mac_address)')

        self.conn.commit()

    def save_scan_result(self, online_hosts, local_ip, network_range):
        """保存扫描结果到数据库

        参数:
            online_hosts: 在线主机列表
            local_ip: 本地IP地址
            network_range: 网络范围
        """
        if not online_hosts:
            return

        scan_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        network_str = str(network_range)

        # 插入数据
        for host in online_hosts:
            self.cursor.execute(
                'INSERT INTO scan_results (scan_time, hostname, ip_address, mac_address, local_ip, network_range, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (scan_time, host['hostname'], host['ip'], host['mac'], local_ip, network_str, 'online')
            )

        self.conn.commit()
        print(f"已将 {len(online_hosts)} 条扫描结果保存到数据库")

    def get_scan_results(self, start_time=None, end_time=None, ip_address=None):
        """查询扫描结果

        参数:
            start_time: 开始时间 (格式: 'YYYY-MM-DD HH:MM:SS')
            end_time: 结束时间 (格式: 'YYYY-MM-DD HH:MM:SS')
            ip_address: IP地址

        返回:
            查询结果列表
        """
        query = 'SELECT * FROM scan_results WHERE 1=1'
        params = []

        if start_time:
            query += ' AND scan_time >= ?'
            params.append(start_time)

        if end_time:
            query += ' AND scan_time <= ?'
            params.append(end_time)

        if ip_address:
            query += ' AND ip_address = ?'
            params.append(ip_address)

        query += ' ORDER BY scan_time DESC'

        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def save_asset_info(self, mac_address, user_name, department, notes):
        """保存资产信息到数据库"""
        registration_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute('''
            INSERT INTO asset_info (mac_address, user_name, department, registration_time, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (mac_address, user_name, department, registration_time, notes))
        self.conn.commit()
        print(f"已保存资产信息: {mac_address}")

    def get_asset_info(self, mac_address):
        """根据MAC地址查询资产信息"""
        self.cursor.execute('SELECT * FROM asset_info WHERE mac_address = ?', (mac_address,))
        return self.cursor.fetchone()

    def update_asset_info(self, mac_address, user_name, department, notes):
        """更新资产信息"""
        registration_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute('''
            UPDATE asset_info 
            SET user_name=?, department=?, registration_time=?, notes=? 
            WHERE mac_address=?
        ''', (user_name, department, registration_time, notes, mac_address))
        self.conn.commit()
        print(f"已更新资产信息: {mac_address}")

    def get_assets_by_macs(self, mac_addresses):
        """根据MAC地址列表批量查询资产信息"""
        if not mac_addresses:
            return []
        placeholders = ', '.join(['?'] * len(mac_addresses))
        self.cursor.execute(f'SELECT mac_address, user_name, department, notes FROM asset_info WHERE mac_address IN ({placeholders})', mac_addresses)
        return self.cursor.fetchall()

    def get_all_assets(self):
        """获取所有资产信息"""
        self.cursor.execute('SELECT mac_address, user_name, department, notes FROM asset_info')
        return self.cursor.fetchall()

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()

    def get_all_ip_addresses(self):
        """获取所有扫描过的IP地址

        返回:
            IP地址列表
        """
        query = 'SELECT DISTINCT ip_address FROM scan_results ORDER BY ip_address'
        self.cursor.execute(query)
        return [row[0] for row in self.cursor.fetchall()]

    def get_last_scan_by_mac(self, mac_address):
        """根据MAC地址获取最后一次扫描记录

        参数:
            mac_address: MAC地址

        返回:
            包含扫描记录的元组，格式为(id, scan_time, hostname, ip_address, mac_address, local_ip, network_range)
            如果没有找到记录则返回None
        """
        self.cursor.execute(
            'SELECT * FROM scan_results WHERE mac_address = ? ORDER BY scan_time DESC LIMIT 1',
            (mac_address,)
        )
        return self.cursor.fetchone()

    def get_all_scanned_macs(self):
        """获取所有扫描过的MAC地址

        返回:
            MAC地址列表
        """
        query = 'SELECT DISTINCT mac_address FROM scan_results ORDER BY mac_address'
        self.cursor.execute(query)
        return [row[0] for row in self.cursor.fetchall()]

    def delete_asset(self, mac_address):
        """根据MAC地址删除资产信息"""
        self.cursor.execute('DELETE FROM asset_info WHERE mac_address = ?', (mac_address,))
        self.conn.commit()

    def delete_scans_by_mac(self, mac_address):
        """根据MAC地址删除所有相关扫描记录"""
        self.cursor.execute('DELETE FROM scan_results WHERE mac_address = ?', (mac_address,))
        self.conn.commit()

def save_results_to_db(online_hosts, local_ip, network_range, db_path='lan_scanner.db'):
    """便捷函数：保存扫描结果到数据库

    参数:
        online_hosts: 在线主机列表
        local_ip: 本地IP地址
        network_range: 网络范围
        db_path: 数据库路径
    """
    db_manager = DatabaseManager(db_path)
    try:
        db_manager.save_scan_result(online_hosts, local_ip, network_range)
    finally:
        db_manager.close()

if __name__ == '__main__':
    # 测试数据库功能
    test_hosts = [
        {'hostname': 'test-host', 'ip': '192.168.1.100', 'mac': '00:11:22:33:44:55', 'status': 'online'}
    ]
    save_results_to_db(test_hosts, '192.168.1.1', '192.168.1.0/24')