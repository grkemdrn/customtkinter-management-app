import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import psycopg2
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings

# Veritabanı bağlantısı
conn = psycopg2.connect(
    database="postgres",
    user="postgres",
    password="135795",
    host="127.0.0.1",
    port=5432,
)

def login(user_name, password):
    try:
        cursor= conn.cursor()
        sql= "SELECT role FROM users WHERE username= %s AND password= %s;"
        cursor.execute (sql,(user_name,password))
        result = cursor.fetchone()
        cursor.close()

        if result:
            return True , result [0]
        else:
            return False, None 
    except Exception as e:
        print(f"Error: {e}")
        return False , None 

def open_experience_filter_window(parent_window):
    filter_window = ctk.CTkToplevel(parent_window)
    filter_window.title("Experience Filter")
    filter_window.geometry("350x320") 
    filter_window.grab_set() # Sadece bu pencereye odaklanmayı zorunlu kılar
    filter_window.focus_force()
    
    ctk.CTkLabel(filter_window, text="Teacher Filtering", font=("Arial", 14, "bold")).pack(pady=(15, 10))

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT class_name FROM announcements")
        courses = ["All Courses"] + [row[0] for row in cursor.fetchall()]
        cursor.close()
    except Exception as e:
        conn.rollback()
        courses = ["All Courses"]

    course_frame = ctk.CTkFrame(filter_window, fg_color="transparent")
    course_frame.pack(pady=5)
    ctk.CTkLabel(course_frame, text="Course:").pack(side="left", padx=(0, 25))
    course_combo = ctk.CTkComboBox(course_frame, values=courses, state="readonly", width=120)
    course_combo.set("All Courses")
    course_combo.pack(side="left")

    min_frame = ctk.CTkFrame(filter_window, fg_color="transparent")
    min_frame.pack(pady=5)
    ctk.CTkLabel(min_frame, text="Minimum (Years):").pack(side="left", padx=5)
    min_entry = ctk.CTkEntry(min_frame, width=120)
    min_entry.pack(side="left")

    max_frame = ctk.CTkFrame(filter_window, fg_color="transparent")
    max_frame.pack(pady=5)
    ctk.CTkLabel(max_frame, text="Maximum (Years):").pack(side="left", padx=5)
    max_entry = ctk.CTkEntry(max_frame, width=120)
    max_entry.pack(side="left")

    def show_pandas_table():
        min_val = min_entry.get()
        max_val = max_entry.get()
        selected_course = course_combo.get()

        if not min_val.isdigit() or not max_val.isdigit():
            print("Please enter valid integers!")
            return

        try:
            if selected_course == "All Courses":
                query = """
                SELECT class_name AS "Course", user_name AS "Teacher", experience_years AS "Experience (Years)", fee AS "Fee (TL)" 
                FROM announcements 
                WHERE experience_years BETWEEN %s AND %s
                ORDER BY experience_years DESC
                """
                params = (int(min_val), int(max_val))
                title_text = f"All Teachers with {min_val} - {max_val} Years of Experience"
            else:
                query = """
                SELECT class_name AS "Course", user_name AS "Teacher", experience_years AS "Experience (Years)", fee AS "Fee (TL)" 
                FROM announcements 
                WHERE experience_years BETWEEN %s AND %s AND class_name = %s
                ORDER BY experience_years DESC
                """
                params = (int(min_val), int(max_val), selected_course)
                title_text = f"{selected_course} Teachers with {min_val} - {max_val} Years of Experience"

            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                df = pd.read_sql_query(query, conn, params=params)

            if df.empty:
                print("No teachers found in this range and selected course.")
                return

            table_window = ctk.CTkToplevel(filter_window)
            table_window.title("Pandas Supported Teacher Table")
            table_window.geometry("700x450")
            table_window.grab_set()

            title_label = ctk.CTkLabel(table_window, text=title_text, font=("Arial", 16, "bold"))
            title_label.pack(pady=(15, 10))

            table_frame = ctk.CTkFrame(table_window)
            table_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

            table_scroll = ttk.Scrollbar(table_frame)
            table_scroll.pack(side="right", fill="y")

            my_tree = ttk.Treeview(table_frame, yscrollcommand=table_scroll.set, columns=list(df.columns), show="headings", height=15)
            my_tree.pack(side="left", fill="both", expand=True)
            table_scroll.config(command=my_tree.yview)

            for col in df.columns:
                my_tree.heading(col, text=col, anchor="center")
                my_tree.column(col, anchor="center", width=150)

            for index, row in df.iterrows():
                my_tree.insert(parent="", index="end", values=list(row))

            style = ttk.Style()
            style.theme_use("default")
            style.configure("Treeview", background="#333333", foreground="white", rowheight=25, fieldbackground="#333333")
            style.map('Treeview', background=[('selected', '#2E86C1')])
            style.configure("Treeview.Heading", background="#555555", foreground="white", font=("Arial", 10, "bold"))

        except Exception as e:
            conn.rollback()
            print(f"Pandas Table Error: {e}")

    ctk.CTkButton(filter_window, text="Create Table", command=show_pandas_table).pack(pady=20)


def plot_student_counts():
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT course_name, COUNT(*) FROM student_selections GROUP BY course_name")
        data = cursor.fetchall()
        cursor.close()

        if not data:
            print("Not enough data for the chart.")
            return

        courses = [row[0] for row in data]
        counts = [row[1] for row in data]

        plt.figure(figsize=(10, 6))
        
        ax = sns.barplot(x=courses, y=counts, palette="magma")
        
        plt.title("Number of Students Selecting Courses", fontsize=14)
        plt.xlabel("Courses", fontsize=12)
        plt.ylabel("Number of Students", fontsize=12)
        plt.xticks(rotation=45)
        plt.yticks(range(0, max(counts) + 15, 10)) 

        for container in ax.containers:
            ax.bar_label(container, fontsize=11, padding=3, fontweight='bold', color='black')

        plt.tight_layout()
        plt.show()
        
    except Exception as e:
        conn.rollback()
        print(f"Student count chart error: {e}")


def plot_fee_and_mode_scatter():
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT class_name, CAST(fee AS NUMERIC), class_mode FROM announcements")
        data = cursor.fetchall()
        cursor.close()

        if not data:
            print("Not enough data for the chart.")
            return

        df = pd.DataFrame(data, columns=["Course", "Fee", "Mode"])

        plt.figure(figsize=(10, 6))
        sns.scatterplot(data=df, x="Fee", y="Course", hue="Mode", palette="Set1", s=150, alpha=0.8)
        
        plt.title("Fee and Education Mode Distribution by Course", fontsize=14, fontweight="bold")
        plt.xlabel("Fee (TL)", fontsize=12)
        plt.ylabel("Course", fontsize=12)
        plt.grid(True, linestyle="--", alpha=0.5)
        
        plt.tight_layout()
        plt.show()

    except Exception as e:
        conn.rollback()
        print(f"Scatterplot error: {e}")


def open_statistics_window(parent_window):
    stats_window = ctk.CTkToplevel(parent_window)
    stats_window.title("Statistics and Charts")
    stats_window.geometry("400x300") 
    stats_window.grab_set()
    
    ctk.CTkLabel(stats_window, text="Select the Chart You Want to View", font=("Arial", 16, "bold")).pack(pady=(20, 10))

    btn_scatter = ctk.CTkButton(stats_window, text="Fee and Education Mode Distribution", command=plot_fee_and_mode_scatter, height=40)
    btn_scatter.pack(pady=15, fill="x", padx=50)

    btn_student_count = ctk.CTkButton(stats_window, text="Number of Students by Course", command=plot_student_counts, height=40)
    btn_student_count.pack(pady=15, fill="x", padx=50)

    btn_pandas_table = ctk.CTkButton(stats_window, text="Teacher Table by Experience", 
                                     command=lambda: open_experience_filter_window(stats_window), height=40, fg_color="#2E86C1")
    btn_pandas_table.pack(pady=15, fill="x", padx=50)


def open_announcement_window(parent_window, refresh_func, current_user):
    announcement_window = ctk.CTkToplevel(parent_window)
    announcement_window.title("New Class Announcement")
    announcement_window.geometry("400x480")
    announcement_window.grab_set()

    ctk.CTkLabel(announcement_window, text="Class Name:").pack(pady=2)
    lessons = ['Math', 'Biology', 'Physics', 'English', 'Turkish', 'Chemistry', 'History', 'Geography','Computer']
    class_combobox = ctk.CTkComboBox(announcement_window, values=lessons, state="readonly")
    class_combobox.set("Select a class") 
    class_combobox.pack(pady=5)

    # Eğitmen adını elle girmek yerine otomatik kendi adını kullanıyoruz
    ctk.CTkLabel(announcement_window, text=f"Instructor: {current_user}", font=("Arial", 12, "bold")).pack(pady=10)

    ctk.CTkLabel(announcement_window, text="Fee (TL):").pack(pady=2)
    entry_fee = ctk.CTkEntry(announcement_window)
    entry_fee.pack()

    ctk.CTkLabel(announcement_window, text="Instructor Age:").pack(pady=2)
    entry_age = ctk.CTkEntry(announcement_window)
    entry_age.pack()

    ctk.CTkLabel(announcement_window, text="Experience (Years):").pack(pady=2)
    entry_experience = ctk.CTkEntry(announcement_window)
    entry_experience.pack()

    ctk.CTkLabel(announcement_window, text="Class Mode:").pack(pady=15)
    selection_var = ctk.IntVar() 
    ctk.CTkRadioButton(announcement_window, text="Online", variable=selection_var, value=1).pack()
    ctk.CTkRadioButton(announcement_window, text="Face to Face", variable=selection_var, value=2).pack()

    def save_announcement():
        class_name = class_combobox.get()
        fee = entry_fee.get()
        instructor_age = entry_age.get()
        experience_years = entry_experience.get()
        mode = "Online" if selection_var.get() == 1 else "Face to Face"

        try:
            cursor = conn.cursor()
            sql = """
                INSERT INTO announcements 
                (class_name, user_name, fee, instructor_age, experience_years, class_mode) 
                VALUES (%s, %s, %s, %s, %s, %s);
            """
            cursor.execute(sql, (class_name, current_user, fee, instructor_age, experience_years, mode))
            conn.commit()
            cursor.close()
            
        except Exception as e:
            print("Database Save Error:", e)
            conn.rollback()

        refresh_func()
        announcement_window.destroy()

    ctk.CTkButton(announcement_window, text="Publish Announcement", command=save_announcement).pack(pady=15)


def open_delete_announcement_window(parent_window, refresh_func, current_user):
    delete_window = ctk.CTkToplevel(parent_window)
    delete_window.title("Delete Announcement")
    delete_window.geometry("600x350")
    delete_window.grab_set()

    ctk.CTkLabel(delete_window, text="Select your announcement to delete:", font=("Arial", 10, "bold")).pack(pady=10)

    listbox = tk.Listbox(delete_window, width=80, height=12)
    listbox.pack(pady=5, padx=10)
    announcement_ids = [] 

    try:
        cursor = conn.cursor()
        # SADECE O ANKİ HOCANIN İLANLARINI ÇEKİYORUZ
        cursor.execute("SELECT id, class_name, user_name, fee, class_mode FROM announcements WHERE user_name = %s ORDER BY id ASC;", (current_user,))
        records = cursor.fetchall()
        for row in records:
            display_text = f"User: {row[2]} | Class: {row[1]} | Fee: {row[3]} TL | Mode: {row[4]}"
            listbox.insert(ctk.END, display_text)
            announcement_ids.append(row[0])
            
        cursor.close()
    except Exception as e:
        print("Error loading list:", e)
        conn.rollback()

    def delete_selected():
        selected_indices = listbox.curselection()
        if not selected_indices:
            status_label.configure(text="Please select an announcement to delete.", text_color="red")
            return

        index = selected_indices[0] 
        announcement_id_to_delete = announcement_ids[index]

        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM announcements WHERE id = %s AND user_name = %s", (announcement_id_to_delete, current_user))
            conn.commit()
            cursor.close()
            
            listbox.delete(index)
            announcement_ids.pop(index) 
            
            status_label.configure(text="Announcement deleted successfully.", text_color="green")
            if refresh_func:
                refresh_func() 
                    
        except Exception as e:
            print("Delete Error:", e)
            conn.rollback()
            status_label.configure(text="A database error occurred during deletion.", text_color="red")

    status_label = ctk.CTkLabel(delete_window, text="", text_color="black")
    status_label.pack(pady=2)
    ctk.CTkButton(delete_window, text="Delete Selected", command=delete_selected, fg_color="red", text_color="white").pack(pady=10)


def open_instructor_dashboard(current_user):
    instructor_window = ctk.CTkToplevel(root)
    instructor_window.title(f"Instructor Dashboard - {current_user}")
    instructor_window.geometry("500x600")
    
    # Kapanınca ana ekranı geri getir
    def on_closing():
        instructor_window.destroy()
        root.deiconify() 
    instructor_window.protocol("WM_DELETE_WINDOW", on_closing)

    quote = '"Education is not the learning of facts,\nbut the training of the mind to think."\n\n- Albert Einstein'
    ctk.CTkLabel(instructor_window, text=quote, font=("Arial", 12, "italic"), text_color="#67947E").pack(pady=20)

    ctk.CTkLabel(instructor_window, text="--- My Active Announcements ---", font=("Poppins", 16, "bold")).pack(pady=10)
    scrollable_frame = ctk.CTkScrollableFrame(instructor_window, width=450, height=300)
    scrollable_frame.pack(pady=5)
    announcements_label = ctk.CTkLabel(scrollable_frame, text="No announcements yet.", justify="left")
    announcements_label.pack(pady=10)

    def refresh_display():
        try:
            cursor = conn.cursor()
            # SADECE KENDİ İLANLARINI LİSTELE
            cursor.execute("SELECT * FROM announcements WHERE user_name = %s;", (current_user,))
            saved_announcements = cursor.fetchall()
            cursor.close()

            if saved_announcements:
                display_list = []
                for row in saved_announcements:
                    announcement_str = f"Class: {row[1]} | Fee: {row[3]} TL | Mode: {row[6]}"
                    display_list.append(announcement_str)
                
                announcements_text = "\n".join(display_list)
                announcements_label.configure(text=announcements_text, text_color="white")
            else:
                announcements_label.configure(text="No announcements yet.", text_color="white")
                
        except Exception as e:
            print("Database Read Error:", e)

    refresh_display()

    main_menu = tk.Menu(instructor_window)
    instructor_window.configure(menu=main_menu)
    
    actions_menu = tk.Menu(main_menu, tearoff=0) 
    main_menu.add_cascade(label="Actions", menu=actions_menu)

    actions_menu.add_command(label="Statistics", command=lambda: open_statistics_window(instructor_window))    
    actions_menu.add_command(label="Add Announcement", command=lambda: open_announcement_window(instructor_window, refresh_display, current_user))
    actions_menu.add_command(label="Delete Announcement", command=lambda: open_delete_announcement_window(instructor_window, refresh_display, current_user))

    def delete_notification(notif_id, window):
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM student_selections WHERE id = %s", (notif_id,))
            conn.commit()
            cursor.close()
            window.destroy()
            show_notifications()
        except Exception as e:
            print("Notification Deletion Error:", e)
            conn.rollback()

    def delete_all_notifications(window):
        try:
            cursor = conn.cursor()
            # SADECE BU HOCANIN DERSLERİYLE İLGİLİ BİLDİRİMLERİ SİL
            cursor.execute("""
                DELETE FROM student_selections 
                WHERE course_name IN (SELECT class_name FROM announcements WHERE user_name = %s)
            """, (current_user,))
            conn.commit()
            cursor.close()
            window.destroy()
            show_notifications()
        except Exception as e:
            print("Error Deleting All Notifications:", e)
            conn.rollback()

    def show_notifications():
        notif_window = ctk.CTkToplevel(instructor_window)
        notif_window.title("Student Course Selection Notifications")
        notif_window.geometry("550x450") 
        notif_window.grab_set()

        ctk.CTkLabel(notif_window, text="--- Incoming Notifications ---", font=("Arial", 12, "bold")).pack(pady=10)
        
        try:
            cursor = conn.cursor()
            # SADECE BU HOCANIN AÇTIĞI DERSLERE GELEN KAYITLARI GÖSTER
            query = """
            SELECT s.id, s.student_name, s.course_name, s.selection_date, MAX(m.email) 
            FROM student_selections s 
            LEFT JOIN mails m ON s.student_name = m.student_name 
            WHERE s.course_name IN (SELECT class_name FROM announcements WHERE user_name = %s)
            GROUP BY s.id, s.student_name, s.course_name, s.selection_date
            ORDER BY s.id DESC
            """
            cursor.execute(query, (current_user,))
            notifications = cursor.fetchall()
            scrooll_frame = ctk.CTkScrollableFrame(notif_window, width=650, height=450)
            scrooll_frame.pack(pady=10, padx=10, fill="both", expand=True)
            cursor.close()

            if notifications:
                for row in notifications:
                    notif_id, student_name, course_name, selection_date, student_email = row[0], row[1], row[2], row[3], row[4]
                    student_email = student_email if student_email else "No Email Provided"

                    notif_text = f"Student: {student_name} | Email: {student_email} | Selected Course: {course_name}"
                    date_text = f"Date: {selection_date}"

                    frame = ctk.CTkFrame(scrooll_frame, border_width=1)
                    frame.pack(fill="x", padx=20, pady=5)
                    
                    text_frame = ctk.CTkFrame(frame, fg_color="transparent")
                    text_frame.pack(side="left", padx=10, pady=5)
                    
                    ctk.CTkLabel(text_frame, text=notif_text, text_color="#F687B7", font=("Arial", 10, "bold"), justify="left").pack(anchor="w")
                    ctk.CTkLabel(text_frame, text=date_text, text_color="white", font=("Arial", 8), justify="left").pack(anchor="w")
                    
                    delete_btn = ctk.CTkButton(frame, text="Delete", width=50, fg_color="#D9534F", hover_color="#C9302C",
                                            command=lambda n_id=notif_id: delete_notification(n_id, notif_window))
                    delete_btn.pack(side="right", padx=10)
                    
                delete_all_btn = ctk.CTkButton(scrooll_frame, text="Delete All", fg_color="#D9534F", hover_color="#C9302C",
                                            command=lambda: delete_all_notifications(notif_window))
                delete_all_btn.pack(pady=(15, 5))
            else:
                ctk.CTkLabel(scrooll_frame, text="No students have selected your courses yet.", text_color="gray", font=("Arial", 12)).pack(pady=20)
 
            refresh_btn = ctk.CTkButton(scrooll_frame, text="Refresh Notifications 🔄", 
                                        command=lambda: [notif_window.destroy(), show_notifications()],
                                        fg_color="lightgray", text_color="black")
            refresh_btn.pack(pady=10)

        except Exception as e:
            print("Notification Read Error:", e)
            conn.rollback()
            ctk.CTkLabel(scrooll_frame, text="A database error occurred while loading notifications.", text_color="red").pack(pady=10)

        
    notifications_button = ctk.CTkButton(instructor_window, 
                                     text="View Notifications 🔔", 
                                     command=show_notifications, 
                                     fg_color="blue", text_color="white",
                                     font=("Poppins", 13, "bold"))
    notifications_button.pack(pady=15)

    def view_student_list():
        list_window = ctk.CTkToplevel(instructor_window)
        list_window.title("Enrolled Students")
        list_window.geometry("450x500")
        list_window.grab_set()
        
        ctk.CTkLabel(list_window, text="--- Students List ---", font=("Arial", 18, "bold")).pack(pady=15)
        scrollable_frame = ctk.CTkScrollableFrame(list_window, width=450, height=300)
        scrollable_frame.pack(pady=5)

        try:
            cursor = conn.cursor()
            # SADECE BU HOCANIN ÖĞRENCİLERİNİ LİSTELE
            query = """
                SELECT student_name, course_name 
                FROM student_selections 
                WHERE course_name IN (SELECT class_name FROM announcements WHERE user_name = %s)
                ORDER BY course_name
            """
            cursor.execute(query, (current_user,))
            all_students = cursor.fetchall()
            cursor.close()

            if all_students:
                for s_name, c_name in all_students:
                    frame = ctk.CTkFrame(scrollable_frame)
                    frame.pack(fill="x", padx=30, pady=2)
                    ctk.CTkLabel(frame, text=f"{s_name} -> {c_name}").pack(pady=5)
            else:
                ctk.CTkLabel(scrollable_frame, text="No students enrolled yet.").pack(pady=20)
                
        except Exception as e:
            print("List Error:", e)

    ctk.CTkButton(instructor_window, text="View Enrolled Students ", font=("Poppins", 13, "bold"), command=view_student_list, fg_color="#A308F6").pack(pady=10)
    

def open_student_dashboard(current_user):
    student_window = ctk.CTkToplevel(root)
    student_window.title(f"Student Dashboard - {current_user}")
    student_window.geometry("500x600")

    def on_closing():
        student_window.destroy()
        root.deiconify()
    student_window.protocol("WM_DELETE_WINDOW", on_closing)

    ctk.CTkLabel(student_window, text="Available Class Announcements",text_color="#BBC2E6", font=("Poppins", 13, "bold")).pack(pady=10)

    filter_frame = ctk.CTkFrame(student_window)
    filter_frame.pack(pady=5)

    ctk.CTkLabel(filter_frame, text="Sort by:").grid(row=0, column=0, padx=5)
    sort_box = ctk.CTkComboBox(filter_frame, values=["Default", "Fee (Ascending)", "Fee (Descending)"], state="readonly")
    sort_box.set("Default")
    sort_box.grid(row=0, column=1, padx=5)

    var_online = tk.IntVar(value=1)  
    var_face = tk.IntVar(value=1)

    ctk.CTkCheckBox(filter_frame, text="Online", variable=var_online, width=20).grid(row=2, column=0, padx=5)
    ctk.CTkCheckBox(filter_frame, text="Face to Face", variable=var_face, width=20).grid(row=2, column=1, padx=5)
    
    ctk.CTkLabel(filter_frame, text="Min Fee:").grid(row=2, column=2, padx=5)
    entry_min_fee = ctk.CTkEntry(filter_frame, width=60)
    entry_min_fee.grid(row=2, column=3, padx=5)

    ctk.CTkLabel(filter_frame, text="Max Fee:").grid(row=2, column=4, padx=5)
    entry_max_fee = ctk.CTkEntry(filter_frame, width=60)
    entry_max_fee.grid(row=2, column=5, padx=5)   
    
    ctk.CTkLabel(filter_frame, text="Filter Class:").grid(row=0, column=2, padx=5)
    filter_lessons = ['All Classes', 'Math', 'Biology', 'Physics', 'English', 'Turkish', 'Chemistry', 'History', 'Geography','Computer']
    filter_box = ctk.CTkComboBox(filter_frame, values=filter_lessons, state="readonly")
    filter_box.set("All Classes") 
    filter_box.grid(row=0, column=3, padx=5)

    list_frame = ctk.CTkFrame(student_window)
    list_frame.pack(pady=10)
    
    scrollbar = ctk.CTkScrollbar(list_frame)
    scrollbar.pack(side=ctk.RIGHT, fill=ctk.Y)
    
    announcement_list = tk.Listbox(list_frame, width=80, height=15,font=("poppins",12), yscrollcommand=scrollbar.set)
    announcement_list.pack(side=ctk.LEFT)
    scrollbar.configure(command=announcement_list.yview)

    status_label = ctk.CTkLabel(student_window, text="", text_color="blue")
    status_label.pack(pady=5)
    
    def fetch_announcements():
        try:
            cursor = conn.cursor()
            selected_class = filter_box.get()
            
            query = "SELECT * FROM announcements WHERE 1=1"
            params = []

            if selected_class != "All Classes":
                query += " AND class_name = %s"
                params.append(selected_class)
            
            active_modes = []
            if var_online.get() == 1: active_modes.append("Online")
            if var_face.get() == 1: active_modes.append("Face to Face")

            if active_modes:
                placeholders = ', '.join(['%s'] * len(active_modes))
                query += f" AND class_mode IN ({placeholders})"
                params.extend(active_modes)
            else:
                query += " AND 1=0" 

            m_val = entry_min_fee.get()
            x_val = entry_max_fee.get()

            if m_val.isdigit():
                query += " AND fee >= %s"
                params.append(int(m_val))
            
            if x_val.isdigit():
                query += " AND fee <= %s"
                params.append(int(x_val))
            
            selection = sort_box.get()
            if selection == "Fee (Ascending)":
                query += " ORDER BY fee ASC"
            elif selection == "Fee (Descending)":
                query += " ORDER BY fee DESC"
             
            cursor.execute(query + ";", params)
            records = cursor.fetchall()
            cursor.close()
                
            announcement_list.delete(0, ctk.END)
            for row in records:
                text = f"User: {row[2]} | Class: {row[1]} | Fee: {row[3]} TL | Mode: {row[6]}"
                announcement_list.insert(ctk.END, text)
                
        except Exception as e:
            print("Read Error:", e)
            conn.rollback()

    def make_reservation():
        selected = announcement_list.curselection()
        if not selected:
            status_label.configure(text="Please select a course from the list!", text_color="red")
            return

        try:
            selected_text = announcement_list.get(selected[0])
            course_name = selected_text.split(" | ")[1].replace("Class: ", "")

            email_window = ctk.CTkToplevel(student_window)
            email_window.title("Contact Information")
            email_window.geometry("400x200")
            email_window.grab_set()

            ctk.CTkLabel(email_window, text="Please enter your email for communication:", font=("Arial", 14)).pack(pady=(20, 10))
            email_entry = ctk.CTkEntry(email_window, width=250, placeholder_text="example@mail.com")
            email_entry.pack(pady=10)

            def confirm_and_save():
                user_email = email_entry.get()
                if not user_email:
                    print("Email field cannot be empty!")
                    return

                try:
                    cursor = conn.cursor()
                    
                    check_query = "SELECT * FROM student_selections WHERE student_name = %s AND course_name = %s"
                    cursor.execute(check_query, (current_user, course_name))
                    existing_record = cursor.fetchone() 
                    
                    if existing_record:
                        status_label.configure(text="You have already booked this course!", text_color="red")
                        email_window.destroy()
                        return 

                    insert_course_query = "INSERT INTO student_selections (student_name, course_name) VALUES (%s, %s)"
                    cursor.execute(insert_course_query, (current_user, course_name))

                    insert_mail_query = "INSERT INTO mails (student_name, email) VALUES (%s, %s)"
                    cursor.execute(insert_mail_query, (current_user, user_email))
                    
                    conn.commit()
                    cursor.close()

                    status_label.configure(text="Reservation created and email saved!", text_color="green")
                    email_window.destroy()

                except Exception as e:
                    print("Reservation Error Details:", type(e).__name__, "-", e)
                    conn.rollback()
                    status_label.configure(text="Database Error! Could not save record.", text_color="red")

            submit_button = ctk.CTkButton(email_window, text="Confirm and Reserve", command=confirm_and_save, fg_color="green")
            submit_button.pack(pady=20)

        except Exception as e:
            print("Read Error:", e)

    def view_my_courses():
        my_courses_window = ctk.CTkToplevel(student_window)
        my_courses_window.title("My Selected Courses")
        my_courses_window.geometry("500x400")
        my_courses_window.grab_set()

        def cancel_course(selection_id):
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM student_selections WHERE id = %s AND student_name = %s", (selection_id, current_user))
                conn.commit()
                cursor.close()
                my_courses_window.destroy()
                view_my_courses()
            except Exception as e:
                print("Cancel Error:", e)
                conn.rollback()

        ctk.CTkLabel(my_courses_window, text="--- My Courses ---", font=("Arial", 12, "bold")).pack(pady=10)

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, course_name, selection_date FROM student_selections WHERE student_name = %s", (current_user,))
            my_selections = cursor.fetchall()
            cursor.close()

            if my_selections:
                for row in my_selections:
                    s_id, c_name, s_date = row
                    frame = ctk.CTkFrame(my_courses_window, border_width=1)
                    frame.pack(fill="x", padx=20, pady=5)
                    ctk.CTkLabel(frame, text=f"Course: {c_name} | Date: {s_date}", font=("Arial", 15)).pack(side="left", padx=10)
                    ctk.CTkButton(frame, text="Cancel", width=60, fg_color="red", command=lambda id=s_id: cancel_course(id)).pack(side="right", padx=10)
            else:
                ctk.CTkLabel(my_courses_window, text="No courses selected.").pack(pady=20)
        except Exception as e:
            print("DB Error:", e)

    ctk.CTkButton(student_window, text="My Selected Courses ", command=view_my_courses, fg_color="#FF4005").pack(pady=5)
    ctk.CTkButton(student_window, text="Refresh List", command=fetch_announcements).pack(pady=5)
    ctk.CTkButton(student_window, text="Book This Class", command=make_reservation, fg_color="green", text_color="white").pack(pady=5)
    ctk.CTkButton(student_window, text="Statistics (Charts)", command=lambda: open_statistics_window(student_window), fg_color="#2E86C1").pack(pady=(10, 5))
    
    fetch_announcements() 


def handle_login():
    username_input = entry_username.get()
    password_input = entry_password.get()
    is_authenticated, user_role = login(username_input, password_input)
    if is_authenticated:
        label_status.configure(text=f"Login Successful! Role: {user_role}", text_color="green")
        
        # Ana giriş sayfasını gizle
        root.withdraw()
        
        # Giriş yapan kullanıcı adını dashboard'a yolla
        if user_role == "instructor":
            open_instructor_dashboard(username_input)
        elif user_role == "student":
            open_student_dashboard(username_input)
    else:
        label_status.configure(text="Error: Invalid username or password", text_color="red")


def register_user(new_username, new_password, role):
    try:
        cursor = conn.cursor()
        sql = "INSERT INTO users (username, password, role) VALUES (%s,%s,%s);"
        cursor.execute(sql, (new_username, new_password, role))
        conn.commit()
        cursor.close()
        return True , "Registration successful!"
    except Exception as e:
        conn.rollback()
        print(f"Database Error: {e}")
        return False , "Registration failed!"

def open_register_window():
    reg_window= ctk.CTkToplevel(root)
    reg_window.title ("Register")
    reg_window.geometry("350x350")
    reg_window.grab_set() # Popup arka plana kaçmasını engeller

    ctk.CTkLabel(reg_window, text="Create New Account", font=("Gotham", 20, "bold")).pack(pady=15)
    ctk.CTkLabel(reg_window, text= "New Username:").pack(pady=5)
    entry_new_user= ctk.CTkEntry (reg_window,width=130)
    entry_new_user.pack()

    ctk.CTkLabel(reg_window, text="New Password:").pack(pady=5)
    entry_new_password = ctk.CTkEntry (reg_window,width=130, show="*")
    entry_new_password.pack()

    ctk.CTkLabel(reg_window, text="Select Role:").pack(pady=5)
    role_combobox= ctk.CTkComboBox(reg_window, values= ["student", "instructor"],state="readonly", width=130)
    role_combobox.set("student")
    role_combobox.pack()

    reg_status_label=ctk.CTkLabel(reg_window, text="")
    reg_status_label.pack(pady=10)

    def submit_registration():
        user_val= entry_new_user.get()
        pass_val= entry_new_password.get()
        role_val= role_combobox.get()

        if user_val == "" or pass_val == "":
            reg_status_label.configure(text="Please fill all fields", text_color="red")
            return
        
        is_success, message = register_user(user_val, pass_val, role_val)

        if is_success :
            reg_status_label.configure(text=message, text_color="green")
            entry_new_user.delete(0, ctk.END)
            entry_new_password.delete(0, ctk.END)
        else:
            reg_status_label.configure(text=message, text_color="red")

    ctk.CTkButton(reg_window,text="Submit Registration", command=submit_registration).pack(pady=5)

root = ctk.CTk()
root.title("Education App- Login")
root.geometry("400x400")

label_title= ctk.CTkLabel(root, text="Login To Your Account", font=("Gotham", 20, "bold"))
label_title.pack(pady=20)

ctk.CTkLabel(root, text="Username:").pack(pady=5)
entry_username = ctk.CTkEntry(root, width=130)
entry_username.pack()

ctk.CTkLabel(root,text="Password:").pack(pady=5)
entry_password= ctk.CTkEntry(root, width=130, show="*")
entry_password.pack()

btn_login= ctk.CTkButton(root,text="Login Now", command=handle_login)
btn_login.pack(pady=20)
btn_register= ctk.CTkButton (root,text="Register New Account", command=open_register_window)
btn_register.pack(pady=5)

label_status= ctk.CTkLabel(root, text="")
label_status.pack(pady=10)

root.mainloop()