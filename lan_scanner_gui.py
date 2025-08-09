# 导入lan_scanner.py中的功能

# 导入数据库管理模块
import csv
import datetime
import os
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import DateEntry

# 导入lan_scanner.py中的功能
import lan_scanner as scanner
from db_manager import DatabaseManager
# 导入数据库管理模块
from db_manager import save_results_to_db

import asyncio


class LanScannerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("局域网主机扫描工具")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        # 初始化状态变量


        # 设置中文字体
        self.style = ttk.Style()
        self.style.configure("Treeview.Heading", font=("SimHei", 10, "bold"))
        self.style.configure("Treeview", font=("SimHei", 10))
        self.style.configure("TButton", font=("SimHei", 10))
        self.style.configure("TLabel", font=("SimHei", 10))
        self.style.configure("TEntry", font=("SimHei", 10))
        self.style.configure("TCheckbutton", font=("SimHei", 10))

        # 扫描状态变量
        self.scanning = False
        self.scan_thread = None
        self.interval = 0
        self.csv_file = None

        # 创建主框架
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 创建控制区域
        self.control_frame = ttk.LabelFrame(self.main_frame, text="扫描控制", padding="10")
        self.control_frame.pack(fill=tk.X, pady=(0, 10))

        # 第一行控制区域
        self.control_row1 = ttk.Frame(self.control_frame)
        self.control_row1.pack(fill=tk.X, pady=(0, 5))

        # 网段输入区域
        self.network_frame = ttk.Frame(self.control_row1)
        self.network_frame.pack(side=tk.LEFT, padx=5)

        self.network_label = ttk.Label(self.network_frame, text=" 网段:")
        self.network_label.pack(side=tk.LEFT)

        self.network_entry = ttk.Entry(self.network_frame, width=15)
        self.network_entry.pack(side=tk.LEFT, padx=5)
        self.network_entry.insert(0, "")  # 留空表示使用本地网络

        self.network_help = ttk.Label(self.network_frame, text="(如:192.168.1.0/24)")
        self.network_help.pack(side=tk.LEFT)

        # 开始扫描按钮
        self.start_button = ttk.Button(self.control_row1, text="开始扫描", command=self.start_scan)
        self.start_button.pack(side=tk.LEFT, padx=5)

        # 停止扫描按钮
        self.stop_button = ttk.Button(self.control_row1, text='停止扫描', command=self.stop_scan, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # 第三行控制区域
        self.control_row3 = ttk.Frame(self.control_frame)
        self.control_row3.pack(fill=tk.X, pady=(5, 0))

        # 排除IP列表选项
        self.exclude_frame = ttk.Frame(self.control_row3)
        self.exclude_frame.pack(side=tk.LEFT, padx=10, pady=5)

        self.exclude_label = ttk.Label(self.exclude_frame, text="排除IP:")
        self.exclude_label.pack(side=tk.LEFT)

        self.exclude_entry = ttk.Entry(self.exclude_frame, width=20)
        self.exclude_entry.pack(side=tk.LEFT, padx=5)
        self.exclude_entry.insert(0, "")

        self.exclude_help = ttk.Label(self.exclude_frame, text="(逗号分隔)")
        self.exclude_help.pack(side=tk.LEFT)

        # 从数据库选择IP按钮
        self.select_from_db_btn = ttk.Button(self.exclude_frame, text="从数据库选择", command=self.select_exclude_ips_from_db)
        self.select_from_db_btn.pack(side=tk.LEFT, padx=5)

        # CSV导出选项
        self.csv_frame = ttk.Frame(self.control_row3)
        self.csv_frame.pack(side=tk.RIGHT, padx=10, pady=5)

        self.csv_var = tk.BooleanVar()
        self.csv_check = ttk.Checkbutton(self.csv_frame, text="导出到CSV:", variable=self.csv_var, command=self.toggle_csv)
        self.csv_check.pack(side=tk.LEFT)

        self.csv_entry = ttk.Entry(self.csv_frame, width=20, state=tk.DISABLED)
        self.csv_entry.pack(side=tk.LEFT, padx=5)
        self.csv_entry.insert(0, "hosts.csv")
        # 当文件路径变化时自动导出
        self.csv_entry.bind('<FocusOut>', lambda e: self.export_to_csv())
        self.csv_entry.bind('<Return>', lambda e: self.export_to_csv())

        self.browse_button = ttk.Button(self.csv_frame, text="浏览...", command=self.browse_csv, state=tk.DISABLED)
        self.browse_button.pack(side=tk.LEFT)

        # 第四行控制区域 - 时间范围查询
        self.control_row4 = ttk.Frame(self.control_frame)
        self.control_row4.pack(fill=tk.X, pady=(5, 0))

        # 时间范围查询区域
        self.time_query_frame = ttk.Frame(self.control_row4)
        self.time_query_frame.pack(side=tk.LEFT, padx=10, pady=5)

        self.start_time_label = ttk.Label(self.time_query_frame, text="开始时间:")
        self.start_time_label.pack(side=tk.LEFT)

        self.start_time_entry = DateEntry(self.time_query_frame, width=10, date_pattern='yyyy-MM-dd')
        self.start_time_entry.pack(side=tk.LEFT, padx=5)
        self.start_hour = ttk.Combobox(self.time_query_frame, width=5, values=[f"{h:02d}" for h in range(24)])
        self.start_hour.set("00")
        self.start_hour.pack(side=tk.LEFT, padx=1)
        self.start_minute = ttk.Combobox(self.time_query_frame, width=5, values=[f"{m:02d}" for m in range(0, 60, 5)])
        self.start_minute.set("00")
        self.start_minute.pack(side=tk.LEFT, padx=1)
        # 设置默认开始时间为24小时前
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        self.start_time_entry.set_date(yesterday)
        self.start_hour.set(yesterday.strftime("%H"))
        self.start_minute.set(yesterday.strftime("%M"))

        self.end_time_label = ttk.Label(self.time_query_frame, text="结束时间:")
        self.end_time_label.pack(side=tk.LEFT, padx=10)

        self.end_time_entry = DateEntry(self.time_query_frame, width=10, date_pattern='yyyy-MM-dd')
        self.end_time_entry.pack(side=tk.LEFT, padx=5)
        self.end_hour = ttk.Combobox(self.time_query_frame, width=5, values=[f"{h:02d}" for h in range(24)])
        self.end_hour.set("00")
        self.end_hour.pack(side=tk.LEFT, padx=1)
        self.end_minute = ttk.Combobox(self.time_query_frame, width=5, values=[f"{m:02d}" for m in range(0, 60, 5)])
        self.end_minute.set("00")
        self.end_minute.pack(side=tk.LEFT, padx=1)
        # 设置默认结束时间为当前时间
        now = datetime.datetime.now()
        self.end_time_entry.set_date(now)
        self.end_hour.set(now.strftime("%H"))
        self.end_minute.set(now.strftime("%M"))

        self.query_button = ttk.Button(self.time_query_frame, text="查询时间段终端", command=self.query_time_range)
        self.query_button.pack(side=tk.LEFT, padx=10)

        # 查询结果显示区域
        self.query_result_frame = ttk.Frame(self.control_row4)
        self.query_result_frame.pack(side=tk.LEFT, padx=20)

        self.online_count_label = ttk.Label(self.query_result_frame, text="在线终端: 0")
        self.online_count_label.pack(side=tk.LEFT, padx=10)

        self.offline_count_label = ttk.Label(self.query_result_frame, text="离线终端: 0")
        self.offline_count_label.pack(side=tk.LEFT, padx=10)

        # 第二行控制区域
        self.control_row2 = ttk.Frame(self.control_frame)
        self.control_row2.pack(fill=tk.X, pady=(5, 0))


        # 扫描模式选择
        self.mode_frame = ttk.Frame(self.control_row2)
        self.mode_frame.pack(side=tk.LEFT, padx=10)

        self.mode_var = tk.StringVar(value="immediate")
        self.mode_immediate = ttk.Radiobutton(self.mode_frame, text="立即扫描", variable=self.mode_var, value="immediate", command=self.toggle_mode)
        self.mode_immediate.pack(side=tk.LEFT)
        self.mode_interval = ttk.Radiobutton(self.mode_frame, text="定时间隔", variable=self.mode_var, value="interval", command=self.toggle_mode)
        self.mode_interval.pack(side=tk.LEFT)

        # 定时扫描选项
        self.interval_frame = ttk.Frame(self.control_row2)
        self.interval_frame.pack(side=tk.LEFT, padx=10)

        self.interval_entry = ttk.Entry(self.interval_frame, width=10, state=tk.DISABLED)
        self.interval_entry.bind("<Return>", self.on_interval_enter)
        self.interval_entry.pack(side=tk.LEFT, padx=5)
        self.interval_entry.insert(0, "300")

        self.interval_label = ttk.Label(self.interval_frame, text="秒")
        self.interval_label.pack(side=tk.LEFT)

        # 指定时间选项
        self.schedule_frame = ttk.Frame(self.control_row2)
        self.schedule_frame.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)

        # 日期时间选择
        self.datetime_label = ttk.Radiobutton(self.schedule_frame, text="指定时间", variable=self.mode_var, value="scheduled", command=self.toggle_mode)
        self.datetime_label.pack(side=tk.LEFT)

        self.datetime_frame = ttk.Frame(self.schedule_frame)
        self.datetime_frame.pack(side=tk.LEFT)

        self.datetime_entry = ttk.Entry(self.datetime_frame, width=16, state=tk.DISABLED)
        self.datetime_entry.pack(side=tk.LEFT)
        self.datetime_entry.insert(0, datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))

        self.calendar_btn = ttk.Button(self.datetime_frame, text="选择", command=self.select_datetime, state=tk.DISABLED)
        self.calendar_btn.pack(side=tk.LEFT, padx=2)

        self.datetime_help = ttk.Label(self.schedule_frame, text="(YYYY-MM-DD HH:MM)")
        self.datetime_help.pack(side=tk.LEFT, padx=5)

        # 创建结果显示区域
        self.result_frame = ttk.LabelFrame(self.main_frame, text="扫描结果", padding="10")
        self.result_frame.pack(fill=tk.BOTH, expand=True)

        # 创建树状视图来显示结果（支持多选）
        columns = ("index", "status", "hostname", "ip", "mac", "user", "department", "notes")
        self.tree = ttk.Treeview(self.result_frame, columns=columns, show="headings", selectmode='extended')

        # 设置列标题
        self.tree.heading("index", text="序号")
        self.tree.heading("status", text="状态")
        self.tree.heading("hostname", text="主机名")
        self.tree.heading("ip", text="IP地址")
        self.tree.heading("mac", text="MAC地址")
        self.tree.heading("user", text="使用人")
        self.tree.heading("department", text="部门")
        self.tree.heading("notes", text="备注")

        # 设置列宽
        self.tree.column("index", width=50, anchor=tk.CENTER)
        self.tree.column("status", width=80, anchor=tk.CENTER)
        self.tree.column("hostname", width=120)
        self.tree.column("ip", width=120)
        self.tree.column("mac", width=180)
        self.tree.column("user", width=100)
        self.tree.column("department", width=100)
        self.tree.column("notes", width=180)

        # 添加滚动条
        self.scrollbar = ttk.Scrollbar(self.result_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=self.scrollbar.set)

        # 放置树状视图和滚动条
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind('<Double-1>', self.on_tree_double_click)

        # 创建右键菜单
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="删除选中", command=self.delete_selected)

        # 绑定右键菜单事件
        self.tree.bind("<Button-3>", self.show_context_menu)

        # 创建状态区域
        self.status_frame = ttk.LabelFrame(self.main_frame, text="状态信息", padding="10")
        self.status_frame.pack(fill=tk.X, pady=(10, 0))

        # 创建文本框显示所有状态信息
        self.status_text = tk.Text(self.status_frame, height=6, width=80, state=tk.DISABLED)
        self.status_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(self.status_frame, command=self.status_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text.config(yscrollcommand=scrollbar.set)

        # 初始化数据库连接
        self.db_manager = DatabaseManager()
        self.add_status("欢迎使用局域网主机扫描工具！")
        self.add_status("点击'开始扫描'按钮开始扫描，留空表示扫描本地网络")

    def on_interval_enter(self, event):
        if self.mode_var.get() == "interval":
            try:
                interval = int(self.interval_entry.get())
                if interval > 0:
                    self.start_scan()
                else:
                    messagebox.showerror("错误", "间隔时间必须大于0秒")
            except ValueError:
                messagebox.showerror("错误", "请输入有效的间隔时间")

    def toggle_mode(self):
        mode = self.mode_var.get()
        if mode == "interval":
            self.interval_entry.config(state=tk.NORMAL)
            self.datetime_entry.config(state=tk.DISABLED)
            self.calendar_btn.config(state=tk.DISABLED)
        elif mode == "scheduled":
            self.interval_entry.config(state=tk.DISABLED)
            self.datetime_entry.config(state=tk.NORMAL)
            self.calendar_btn.config(state=tk.NORMAL)
        else:
            self.interval_entry.config(state=tk.DISABLED)
            self.datetime_entry.config(state=tk.DISABLED)
            self.calendar_btn.config(state=tk.DISABLED)

    def select_datetime(self):
        current_text = self.datetime_entry.get()
        try:
            current_dt = datetime.datetime.strptime(current_text, "%Y-%m-%d %H:%M")
        except ValueError:
            current_dt = datetime.datetime.now()
        
        # 创建日期时间选择对话框
        top = tk.Toplevel(self.root)
        top.title("选择日期时间")
        top.geometry("300x250")
        top.resizable(False, False)
        
        # 日期选择
        date_label = ttk.Label(top, text="选择日期:")
        date_label.pack(pady=5)
        cal = DateEntry(top, width=12, datefmt='yyyy-mm-dd', 
                       year=current_dt.year, month=current_dt.month, day=current_dt.day)
        cal.pack(pady=5)
        
        # 时间选择
        time_label = ttk.Label(top, text="选择时间:")
        time_label.pack(pady=5)
        
        time_frame = ttk.Frame(top)
        time_frame.pack(pady=5)
        
        hour_var = tk.StringVar(value=f"{current_dt.hour:02d}")
        minute_var = tk.StringVar(value=f"{current_dt.minute:02d}")
        
        hour_entry = ttk.Entry(time_frame, width=5, textvariable=hour_var)
        hour_entry.pack(side=tk.LEFT, padx=5)
        colon_label = ttk.Label(time_frame, text=":")
        colon_label.pack(side=tk.LEFT)
        minute_entry = ttk.Entry(time_frame, width=5, textvariable=minute_var)
        minute_entry.pack(side=tk.LEFT, padx=5)
        
        def set_datetime():
            try:
                selected_date = cal.get_date()
                hour = int(hour_var.get())
                minute = int(minute_var.get())
                
                if 0 <= hour < 24 and 0 <= minute < 60:
                    selected_dt = datetime.datetime.combine(selected_date, datetime.time(hour, minute))
                    self.datetime_entry.delete(0, tk.END)
                    self.datetime_entry.insert(0, selected_dt.strftime("%Y-%m-%d %H:%M"))
                    top.destroy()
                # 自动启动定时扫描
                if self.mode_var.get() == "scheduled":
                    self.start_scan()
                else:
                    messagebox.showerror("错误", "无效的时间格式，请输入0-23的小时和0-59的分钟")
            except ValueError as e:
                messagebox.showerror("错误", f"无效的输入: {e}")
        
        ok_btn = ttk.Button(top, text="确定", command=set_datetime)
        ok_btn.pack(pady=10)
        
        # 居中显示对话框
        top.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (top.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (top.winfo_height() // 2)
        top.geometry(f"+{x}+{y}")
        top.grab_set()  # 模态对话框
        self.root.wait_window(top)

    def toggle_csv(self):
        if self.csv_var.get():
            self.csv_entry.config(state=tk.NORMAL)
            self.browse_button.config(state=tk.NORMAL)
            # 如果已有扫描结果，立即导出
            if hasattr(self, 'scan_results') and self.scan_results:
                self.export_to_csv()
        else:
            self.csv_entry.config(state=tk.DISABLED)
            self.browse_button.config(state=tk.DISABLED)

    def browse_csv(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.csv_entry.delete(0, tk.END)
            self.csv_entry.insert(0, filename)

    def add_status(self, message):
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)

    def on_tree_double_click(self, event):
        try:
            selected_item = self.tree.selection()[0]
            mac_address = self.tree.item(selected_item, 'values')[4]
            self.open_asset_registration_dialog(mac_address)
        except (IndexError, KeyError):
            pass

    def open_asset_registration_dialog(self, mac_address):
        # 查询已登记的资产信息
        asset_info = self.db_manager.get_asset_info(mac_address)
        is_new = asset_info is None

        top = tk.Toplevel(self.root)
        top.title("资产信息登记" if is_new else "资产信息查看/编辑")
        top.geometry("400x350")
        top.resizable(False, False)

        # 居中显示
        top.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (top.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (top.winfo_height() // 2)
        top.geometry(f"+{x}+{y}")

        # 创建表单
        ttk.Label(top, text="MAC地址:").grid(row=0, column=0, padx=10, pady=5, sticky=tk.W)
        ttk.Label(top, text=mac_address).grid(row=0, column=1, padx=10, pady=5, sticky=tk.W)

        if not is_new:
            # 显示登记时间
            reg_time_label = ttk.Label(top, text="登记时间:")
            reg_time_label.grid(row=1, column=0, padx=10, pady=5, sticky=tk.W)
            reg_time_value = ttk.Label(top, text=asset_info[4])
            reg_time_value.grid(row=1, column=1, padx=10, pady=5, sticky=tk.W)
            row_offset = 1
        else:
            row_offset = 0

        ttk.Label(top, text="用户名:").grid(row=1+row_offset, column=0, padx=10, pady=5, sticky=tk.W)
        user_entry = ttk.Entry(top, width=30)
        user_entry.grid(row=1+row_offset, column=1, padx=10, pady=5)

        ttk.Label(top, text="部门:").grid(row=2+row_offset, column=0, padx=10, pady=5, sticky=tk.W)
        dept_entry = ttk.Entry(top, width=30)
        dept_entry.grid(row=2+row_offset, column=1, padx=10, pady=5)

        ttk.Label(top, text="备注:").grid(row=3+row_offset, column=0, padx=10, pady=5, sticky=tk.NW)
        notes_text = tk.Text(top, width=30, height=5)
        notes_text.grid(row=3+row_offset, column=1, padx=10, pady=5)

        # 如果是已登记资产，填充现有数据
        if not is_new:
            user_entry.insert(0, asset_info[2] or "")
            dept_entry.insert(0, asset_info[3] or "")
            notes_text.insert("1.0", asset_info[5] or "")

        def save_asset():
            username = user_entry.get().strip()
            department = dept_entry.get().strip()
            notes = notes_text.get("1.0", tk.END).strip()

            if not username or not department:
                messagebox.showerror("错误", "用户名和部门不能为空")
                return

            try:
                if is_new:
                    self.db_manager.save_asset_info(
                        mac_address=mac_address,
                        user_name=username,
                        department=department,
                        notes=notes
                    )
                    messagebox.showinfo("成功", "资产信息已保存")
                    self.refresh_list()
                else:
                    self.db_manager.update_asset_info(
                        mac_address=mac_address,
                        user_name=username,
                        department=department,
                        notes=notes
                    )
                    messagebox.showinfo("成功", "资产信息已更新")
                    self.refresh_list()
                top.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"操作失败: {str(e)}")

        btn_frame = ttk.Frame(top)
        btn_frame.grid(row=4+row_offset, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="保存" if is_new else "更新", command=save_asset).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=top.destroy).pack(side=tk.LEFT, padx=5)

        top.grab_set()
        self.root.wait_window(top)
        self.root.update_idletasks()

    def select_exclude_ips_from_db(self):
        """从数据库选择要排除的IP地址"""
        try:
            # 创建数据库连接
            from db_manager import DatabaseManager
            db_manager = DatabaseManager()
            all_ips = db_manager.get_all_ip_addresses()
            db_manager.close()

            if not all_ips:
                messagebox.showinfo("提示", "数据库中没有找到扫描记录")
                return

            # 创建选择对话框
            dialog = tk.Toplevel(self.root)
            dialog.title("选择排除IP")
            dialog.geometry("400x300")
            dialog.transient(self.root)
            dialog.grab_set()

            # 创建列表框和滚动条
            list_frame = ttk.Frame(dialog)
            list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            scrollbar = ttk.Scrollbar(list_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            ip_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, yscrollcommand=scrollbar.set, font=("SimHei", 10))
            ip_listbox.pack(fill=tk.BOTH, expand=True)
            scrollbar.config(command=ip_listbox.yview)

            # 填充IP地址
            for ip in all_ips:
                ip_listbox.insert(tk.END, ip)

            # 确认按钮
            def confirm_selection():
                selected_indices = ip_listbox.curselection()
                if selected_indices:
                    selected_ips = [ip_listbox.get(i) for i in selected_indices]
                    current_ips = self.exclude_entry.get().strip()
                    if current_ips:
                        # 合并现有IP和选中的IP
                        current_ip_list = [ip.strip() for ip in current_ips.split(',') if ip.strip()]
                        combined_ips = list(set(current_ip_list + selected_ips))
                        self.exclude_entry.delete(0, tk.END)
                        self.exclude_entry.insert(0, ','.join(combined_ips))
                    else:
                        self.exclude_entry.delete(0, tk.END)
                        self.exclude_entry.insert(0, ','.join(selected_ips))
                dialog.destroy()

            # 按钮框架
            btn_frame = ttk.Frame(dialog)
            btn_frame.pack(fill=tk.X, padx=10, pady=10)

            select_all_btn = ttk.Button(btn_frame, text="全选", command=lambda: ip_listbox.select_set(0, tk.END))
            select_all_btn.pack(side=tk.LEFT, padx=5)

            deselect_all_btn = ttk.Button(btn_frame, text="取消全选", command=lambda: ip_listbox.selection_clear(0, tk.END))
            deselect_all_btn.pack(side=tk.LEFT, padx=5)

            confirm_btn = ttk.Button(btn_frame, text="确认", command=confirm_selection)
            confirm_btn.pack(side=tk.RIGHT, padx=5)

            cancel_btn = ttk.Button(btn_frame, text="取消", command=dialog.destroy)
            cancel_btn.pack(side=tk.RIGHT, padx=5)

        except Exception as e:
            messagebox.showerror("错误", f"从数据库选择IP时出错: {e}")
            self.add_status(f"从数据库选择IP时出错: {e}")

    def clear_results(self):
        """清空表格中的所有结果"""
        for item in self.tree.get_children():
            self.tree.delete(item)

    def query_time_range(self):
        try:
            # 获取时间范围
            start_datetime = self.start_time_entry.get_date()
            end_datetime = self.end_time_entry.get_date()

            if start_datetime > end_datetime:
                messagebox.showerror("错误", "开始时间不能晚于结束时间")
                return

            # 格式化时间字符串
            # 组合日期和时间
            start_hour = int(self.start_hour.get())
            start_minute = int(self.start_minute.get())
            start_datetime = datetime.datetime.combine(start_datetime, datetime.time(start_hour, start_minute))
            
            end_hour = int(self.end_hour.get())
            end_minute = int(self.end_minute.get())
            end_datetime = datetime.datetime.combine(end_datetime, datetime.time(end_hour, end_minute))
            
            # 格式化时间字符串为YYYY-MM-DD HH:MM
            # 包含秒数以匹配数据库中的时间格式
            start_time = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
            end_time = end_datetime.strftime('%Y-%m-%d %H:%M:%S')

            # 查询数据库获取时间段内的扫描结果
            self.db_manager.cursor.execute(
                "SELECT DISTINCT ip_address, status, hostname, mac_address FROM scan_results WHERE scan_time BETWEEN ? AND ?",
                (start_time, end_time)
            )
        except Exception as e:
            messagebox.showerror("错误", f"查询失败: {str(e)}")
            self.add_status(f"查询错误: {str(e)}")
            return

        results = self.db_manager.cursor.fetchall()
        
        # 清空现有结果
        self.clear_results()
        
        # 显示无结果提示
        if not results:
            messagebox.showinfo("提示", "该时间段内没有扫描结果")
            return
        
        # 处理结果以确定每个IP的最终状态
        ip_status = {}
        for ip_address, status, hostname, mac_address in results:
            if ip_address not in ip_status:
                ip_status[ip_address] = {'status': 'offline', 'hostname': hostname or '未知', 'mac': mac_address or '未知'}
            if status == 'online':
                ip_status[ip_address]['status'] = 'online'

        # 统计并显示结果
        online_count = sum(1 for item in ip_status.values() if item['status'] == 'online')
        offline_count = len(ip_status) - online_count
        
        # 更新标签显示
        self.online_count_label.config(text=f"在线终端: {online_count}")
        self.offline_count_label.config(text=f"离线终端: {offline_count}")
        
        # 准备排序数据
        sorted_list = []
        for ip, info in ip_status.items():
              asset_info = self.db_manager.get_asset_info(info['mac'])
              if asset_info:
                  status_db = info['status']
                  user_name = asset_info[2] or '未登记'
                  department = asset_info[3] or '未登记'
                  note = asset_info[5] or ''
                  status = '在线' if status_db == 'online' else '离线' if status_db == 'offline' else '未登记'
              else:
                  status = '未登记'
                  user_name = ''
                  department = ''
                  note = ''
              # 分配权重：在线(0) > 离线(1) > 未登记(2)
              weight = 0 if status == '在线' else 1 if status == '离线' else 2
              sorted_list.append( (weight, ip, info, user_name, department, status, note) )
          
        # 按权重排序
        sorted_list.sort(key=lambda x: x[0])
        
        # 在表格中显示结果
        for i, (weight, ip, info, user_name, department, status, note) in enumerate(sorted_list, 1):
            self.tree.insert('', tk.END, values=(
                i, status, info['hostname'], ip, info['mac'],
                user_name, department, note  # 备注留空
            ))
        
        self.add_status(f"查询完成: 在线{online_count}台, 离线{offline_count}台 (时间段: {start_time} 至 {end_time})")

    def on_interval_enter(self, event):
        if self.mode_var.get() == "interval":
            try:
                interval = int(self.interval_entry.get())
                if interval > 0:
                    self.start_scan()
                else:
                    messagebox.showerror("错误", "间隔时间必须大于0秒")
            except ValueError:
                messagebox.showerror("错误", "请输入有效的间隔时间")

    def export_to_csv(self):
        """导出扫描结果或查询结果到CSV文件"""
        # 检查是否有查询结果
        if self.tree.get_children():
            # 导出查询结果
            items = self.tree.get_children()
            if not items:
                self.add_status("没有可导出的查询结果")
                return

            # 获取用户指定的文件路径
            csv_file = self.csv_entry.get().strip()
            if not csv_file:
                csv_file = 'query_results.csv'
                self.csv_entry.insert(0, csv_file)
            
            export_path = csv_file
            if not os.path.isabs(export_path):
                export_path = os.path.join(os.getcwd(), export_path)

            try:
                with open(export_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    # 写入表头
                    writer.writerow(["序号", "状态", "主机名", "IP地址", "MAC地址", "使用人", "部门", "备注"])

                    # 写入数据行
                    for item in items:
                        values = self.tree.item(item, "values")
                        writer.writerow(values)

                self.add_status(f"查询结果已导出到 {export_path}")
                return
            except Exception as e:
                self.add_status(f"导出失败: {str(e)}")
                return

        # 否则导出扫描结果
        if not hasattr(self, 'scan_results') or not self.scan_results:
            self.add_status("没有可导出的扫描结果")
            return

        # 获取用户指定的文件路径
        csv_file = self.csv_entry.get().strip()
        if not csv_file:
            csv_file = 'scan_results.csv'
            self.csv_entry.insert(0, csv_file)
        
        export_path = csv_file
        if not os.path.isabs(export_path):
            export_path = os.path.join(os.getcwd(), export_path)

        try:
            with open(export_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.scan_results[0].keys())
                writer.writeheader()
                writer.writerows(self.scan_results)
            self.add_status(f"扫描结果已导出到 {export_path}")
        except Exception as e:
            self.add_status(f"导出失败: {str(e)}")

    def show_context_menu(self, event):
        """显示右键菜单"""
        # 获取点击位置的项
        item = self.tree.identify_row(event.y)
        if item:
            # 选中点击的项
            self.tree.selection_set(item)
            # 显示菜单
            self.context_menu.post(event.x_root, event.y_root)

    def delete_selected(self):
        # 获取选中项
        selected_items = self.tree.selection()
        if not selected_items:
            self.add_status("请先选择要删除的记录")
            return
            
        # 获取选中的MAC地址
        mac_addresses = []
        for item in selected_items:
            values = self.tree.item(item, 'values')
            mac_address = values[4]  # MAC地址在第5列
            mac_addresses.append(mac_address)
            
        try:
            # 从数据库中删除记录
            deleted_count = 0
            for mac in mac_addresses:
                # 删除资产信息
                self.db_manager.delete_asset(mac)
                # 删除扫描记录
                self.db_manager.delete_scans_by_mac(mac)
                deleted_count += 1
                
            # 刷新扫描结果
            self.add_status(f"已成功删除{deleted_count}条记录")
            self.refresh_list()
        except Exception as e:
            self.add_status(f"删除失败: {str(e)}")

    def refresh_list(self, online_hosts=None):
        """刷新资产列表，包含已登记和未登记资产"""
        # 清除现有结果
        self.clear_results()
        
        # 确保online_hosts是列表类型
        if online_hosts is None:
            online_hosts = []
            # 如果没有提供在线主机列表，从数据库获取最新扫描结果
            try:
                # 直接查询数据库获取最新扫描结果
                self.db_manager.cursor.execute("""
                    SELECT ip_address, status FROM scan_results 
                    WHERE scan_time = (SELECT MAX(scan_time) FROM scan_results)
                """)
                latest_scan = self.db_manager.cursor.fetchall()
                if latest_scan:
                    online_hosts = [{'ip': ip} for ip, status in latest_scan if status == 'online']
            except Exception as e:
                self.add_status(f"获取最新扫描结果失败: {str(e)}")

        # 从数据库获取所有资产，确保返回列表而非None
        all_assets = self.db_manager.get_all_assets() or []
        # 获取所有扫描过的MAC地址，确保返回列表而非None
        scanned_macs = self.db_manager.get_all_scanned_macs() or []

        # 已登记资产的MAC集合
        registered_macs = {asset[0] for asset in all_assets}
        # 未登记但已扫描的MAC集合
        unregistered_macs = [mac for mac in scanned_macs if mac not in registered_macs]

        # 处理已登记资产
        for idx, asset in enumerate(all_assets, 1):
            mac_address = asset[0]
            user_name = asset[1] or ""
            department = asset[2] or ""
            notes = asset[3] or ""
            
            # 获取主机名和IP地址
            last_scan = self.db_manager.get_last_scan_by_mac(mac_address)
            hostname = last_scan[2] if last_scan else "未知"
            ip_address = last_scan[3] if last_scan else "未知"
            
            # 检查资产是否在线
            is_online = False
            if ip_address != "未知":
                is_online = any(host.get('ip') == ip_address for host in online_hosts)

            status = "在线" if is_online else "离线"
            
            # 插入表格
            self.tree.insert("", tk.END, values=(
                idx, status, hostname, ip_address, mac_address, user_name, department, notes
            ))
        
        # 处理未登记资产
        for mac_address in unregistered_macs:
            # 获取主机名和IP地址
            last_scan = self.db_manager.get_last_scan_by_mac(mac_address)
            hostname = last_scan[2] if last_scan else "未知"
            ip_address = last_scan[3] if last_scan else "未知"

            # 检查是否在线
            is_online = False
            if ip_address != "未知":
                is_online = any(host.get('ip') == ip_address for host in online_hosts)

            status = "在线" if is_online else "离线"
            # 未登记资产状态显示为"未登记"
            status = "未登记"

            # 插入表格（序号延续已登记资产）
            self.tree.insert("", tk.END, values=(
                len(all_assets) + unregistered_macs.index(mac_address) + 1,
                status, hostname, ip_address, mac_address, "", "", ""
            ))

        total_count = len(all_assets) + len(unregistered_macs)
        self.add_status(f"已刷新 {total_count} 条记录（已登记: {len(all_assets)}, 未登记: {len(unregistered_macs)}）")


        if self.csv_var.get():
            self.export_to_csv()

    async def scan_network(self):
        try:
            self.add_status("开始扫描，请稍候...")
            # 获取自定义网段
            network_range = self.network_entry.get().strip()
            if network_range:
                self.add_status(f"使用自定义网段: {network_range}")
            
            if hasattr(self, 'exclude_ips') and self.exclude_ips:
                self.add_status(f"排除IP列表: {', '.join(self.exclude_ips)}")
                # 确保scanner.scan_network返回的是协程
                online_hosts, local_ip, network = await scanner.scan_network(exclude_ips=self.exclude_ips, network_range=network_range)
            else:
                online_hosts, local_ip, network = await scanner.scan_network(network_range=network_range)

            self.add_status(f"本地IP地址: {local_ip}")
            self.add_status(f"扫描网络范围: {network}")
            
            # 保存结果到数据库
            try:
                save_results_to_db(online_hosts, local_ip, network)
                self.add_status("扫描结果已保存到数据库")
            except Exception as db_e:
                self.add_status(f"保存到数据库时出错: {db_e}")
            
            self.root.after(0, lambda: self.refresh_list(online_hosts))
        except Exception as e:
            self.add_status(f"扫描出错: {e}")
            self.root.after(0, lambda: self.stop_scan())

    def start_scan(self):
        if self.scanning:
            return

        # 获取参数
        try:
            mode = self.mode_var.get()
            self.interval = 0
            self.schedule_time = None

            if mode == "interval":
                self.interval = int(self.interval_entry.get())
                if self.interval <= 0:
                    messagebox.showerror("错误", "间隔时间必须大于0秒")
                    return
            elif mode == "scheduled":
                time_str = self.datetime_entry.get().strip()
                if not time_str:
                    messagebox.showerror("错误", "请输入有效的时间")
                    return
                # 验证时间格式 HH:MM:SS
                try:
                    dt = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M")
                    h, m, s = dt.hour, dt.minute, 0
                    if h < 0 or h > 23 or m < 0 or m > 59:
                        raise ValueError
                    self.scheduled_datetime = dt
                except ValueError:
                    messagebox.showerror("错误", "时间格式无效，请使用YYYY-MM-DD HH:MM格式")
                    return

            if self.csv_var.get():
                self.csv_file = self.csv_entry.get()
            else:
                self.csv_file = None

            # 获取排除IP列表
            exclude_ips_text = self.exclude_entry.get().strip()
            self.exclude_ips = []
            if exclude_ips_text:
                self.exclude_ips = [ip.strip() for ip in exclude_ips_text.split(',') if ip.strip()]
        except ValueError:
            messagebox.showerror("错误", "请输入有效的间隔时间")
            return

        # 更新按钮状态
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.csv_check.config(state=tk.DISABLED)

        self.scanning = True

        # 启动扫描线程
        self.scan_thread = threading.Thread(target=self.scan_loop)
        self.scan_thread.daemon = True
        self.scan_thread.start()

    def scan_loop(self):
        mode = self.mode_var.get()

        if mode == "scheduled":
            # 计算等待时间
            try:
                now = datetime.datetime.now()
                delta = self.scheduled_datetime - now
                if delta.total_seconds() < 0:
                    delta += datetime.timedelta(days=1)
                    self.root.after(0, lambda: self.add_status(f"指定时间已过，将在明天 {self.scheduled_datetime.strftime('%Y-%m-%d %H:%M')} 执行扫描..."))
                else:
                    self.root.after(0, lambda: self.add_status(f"将在 {self.scheduled_datetime.strftime('%Y-%m-%d %H:%M')} 执行扫描，等待 {int(delta.total_seconds())} 秒..."))
                time.sleep(delta.total_seconds())
                
                if self.scanning:
                    # 创建新事件循环运行异步扫描
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(self.scan_network())
                    finally:
                        loop.close()
                    self.root.after(0, self.stop_scan)
            except Exception as e:
                self.root.after(0, lambda: self.add_status(f"时间调度出错: {e}"))
                self.root.after(0, self.stop_scan)
        else:
            # 立即扫描或定时间隔模式
            first_run = True
            while self.scanning:
                if first_run and self.interval > 0:
                    self.root.after(0, lambda: self.add_status(f"将在 {self.interval} 秒后开始第一次扫描..."))
                    time.sleep(self.interval)
                    first_run = False
                elif not first_run and self.interval > 0:
                    self.root.after(0, lambda: self.add_status(f"将在 {self.interval} 秒后再次扫描..."))
                    time.sleep(self.interval)

                if self.scanning:
                    # 创建新事件循环运行异步扫描
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(self.scan_network())
                    finally:
                        loop.close()

                # 如果是单次扫描，完成后退出循环
                if self.interval <= 0 and self.scanning:
                    self.root.after(0, self.stop_scan)
                    break

    def stop_scan(self):
        if not self.scanning:
            return

        self.scanning = False

        # 等待扫描线程结束
        if self.scan_thread and self.scan_thread.is_alive():
            self.scan_thread.join(timeout=1.0)

        # 更新按钮状态
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.csv_check.config(state=tk.NORMAL)
        self.add_status("扫描已停止")

def main():
    try:
        # 检查tabulate是否已安装
        import tabulate
    except ImportError:
        print("错误: 缺少必要的依赖包 'tabulate'。")
        print("请运行: pip install tabulate")
        exit(1)
    try:
        # 检查tkinter是否已安装
        import tkinter as tk
    except ImportError:
        print("错误: 缺少必要的依赖包 'tkinter'。")
        print("请运行: sudo apt install python3-tk")
        exit(1)
    try:
        # 检查asyncio是否已安装
        import asyncio
    except ImportError:
        print("错误: 缺少必要的依赖包 'asyncio'。")
        print("请运行: pip install asyncio")
        exit(1)
    try:
        # 检查threading是否已安装
        import threading
    except ImportError:
        print("错误: 缺少必要的依赖包 'threading'。")
        print("请运行: pip install threading")
        exit(1)
    try:
        # 检查datetime是否已安装
        import datetime
    except ImportError:
        print("错误: 缺少必要的依赖包 'datetime'。")
        print("请运行: pip install datetime")
        exit(1)
    try:
        # 检查time是否已安装
        import time
    except ImportError:
        print("错误: 缺少必要的依赖包 'time'。")
        print("请运行: pip install time")
        exit(1)
    try:
        # 检查messagebox是否已安装
        import tkinter.messagebox
    except ImportError:
        print("错误: 缺少必要的依赖包 'tkinter.messagebox'。")
        print("请运行: pip install tkinter.messagebox")
        exit(1)
    try:
        # 检查tkinter是否已安装
        import tkinter as tk
    except ImportError:
        print("错误: 缺少必要的依赖包 'tkinter'。")
        print("请运行: sudo apt install python3-tk")
        exit(1)

    root = tk.Tk()
    app = LanScannerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()


