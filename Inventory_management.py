import sqlite3
from tkinter import Tk, Label, Button, Entry, messagebox, StringVar, ttk, Toplevel, IntVar, Canvas, Frame, Spinbox


class InventoryManagementApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Inventory Management System")

        # Database initialization
        self.db_path = "company_inventory.db"
        self.create_connection()
        self.ensure_schema()
        self.initialize_ui()

        # Bind the close button (X) to the on_close method
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_connection(self):
        """
        Create a database connection and keep it open.
        """
        try:
            self.conn = sqlite3.connect(self.db_path)
            # Enable foreign key support
            self.conn.execute("PRAGMA foreign_keys = 1")
        except sqlite3.Error as e:
            messagebox.showerror("Database Connection Error", str(e))
            self.root.quit()

    def ensure_schema(self):
        """
        Ensure that the database schema matches the program's requirements.
        """
        try:
            cursor = self.conn.cursor()

            # Ensure Inventory table has required structure, including UNIQUE constraint for 'name'
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Inventory (
                    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Products (
                    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ProductRequirements (
                    req_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    item_id INTEGER NOT NULL,
                    required_quantity INTEGER NOT NULL,
                    FOREIGN KEY(product_id) REFERENCES Products(product_id) ON DELETE CASCADE,
                    FOREIGN KEY(item_id) REFERENCES Inventory(item_id)
                )
            ''')
            self.conn.commit()
        except sqlite3.Error as e:
            messagebox.showerror("Schema Creation Error", str(e))

    def initialize_ui(self):
        tab_control = ttk.Notebook(self.root)

        self.inventory_tab = ttk.Frame(tab_control)
        self.product_tab = ttk.Frame(tab_control)

        tab_control.add(self.inventory_tab, text="Manage Inventory")
        tab_control.add(self.product_tab, text="Manage Products")
        tab_control.pack(expand=1, fill="both")

        self.setup_inventory_tab()
        self.setup_product_tab()

    def setup_inventory_tab(self):
        """
        Setup the Inventory Management Tab.
        """
        frame = ttk.Frame(self.inventory_tab)
        frame.pack(pady=10, padx=10)

        Label(frame, text="Item Name").grid(row=0, column=0, padx=10, pady=5)
        Label(frame, text="Quantity").grid(row=1, column=0, padx=10, pady=5)
        Label(frame, text="Price").grid(row=2, column=0, padx=10, pady=5)

        self.item_name_var = StringVar()
        self.item_quantity_var = StringVar()
        self.item_price_var = StringVar()

        Entry(frame, textvariable=self.item_name_var).grid(row=0, column=1, padx=10, pady=5)
        Entry(frame, textvariable=self.item_quantity_var).grid(row=1, column=1, padx=10, pady=5)
        Entry(frame, textvariable=self.item_price_var).grid(row=2, column=1, padx=10, pady=5)

        Button(frame, text="Add/Update Item", command=self.add_or_update_item).grid(row=3, column=0, columnspan=2, pady=10)

        self.inventory_tree = ttk.Treeview(self.inventory_tab, columns=("Serial", "ID", "Name", "Quantity", "Price"), show="headings")
        self.inventory_tree.heading("Serial", text="Serial No.")
        self.inventory_tree.heading("ID", text="ID")
        self.inventory_tree.heading("Name", text="Name")
        self.inventory_tree.heading("Quantity", text="Quantity")
        self.inventory_tree.heading("Price", text="Price")
        
        # Adjust column widths
        self.inventory_tree.column("Serial", width=50, anchor='center')
        self.inventory_tree.column("ID", width=50, anchor='center')
        self.inventory_tree.pack(pady=10, padx=10)

        Button(frame, text="Delete Selected Item", command=self.delete_selected_item).grid(row=4, column=0, columnspan=2, pady=10)

        self.refresh_inventory()

    def setup_product_tab(self):
        """
        Setup the Product Management Tab.
        """
        frame = ttk.Frame(self.product_tab)
        frame.pack(pady=10, padx=10)

        Button(frame, text="Add Product", command=self.show_add_product_popup).grid(row=0, column=0, padx=10, pady=10)
        Button(frame, text="View Product Details", command=self.view_product_details).grid(row=0, column=1, padx=10, pady=10)

        self.product_tree = ttk.Treeview(self.product_tab, columns=("ID", "Name", "Units Buildable"), show="headings")
        self.product_tree.heading("ID", text="ID")
        self.product_tree.heading("Name", text="Name")
        self.product_tree.heading("Units Buildable", text="Units Buildable")
        self.product_tree.pack(pady=10, padx=10)

        Button(frame, text="Delete Selected Product", command=self.delete_selected_product).grid(row=1, column=0, columnspan=2, pady=10)

        self.refresh_products()

    def add_or_update_item(self):
        """
        Add or update an inventory item.
        """
        name = self.item_name_var.get().strip()
        quantity = self.item_quantity_var.get().strip()
        price = self.item_price_var.get().strip()

        if not name or not quantity.isdigit() or not price.replace('.', '', 1).isdigit():
            messagebox.showerror("Error", "Invalid input")
            return

        try:
            cursor = self.conn.cursor()
            # First, check if the item already exists
            cursor.execute("SELECT item_id FROM Inventory WHERE name = ?", (name,))
            existing_item = cursor.fetchone()

            if existing_item:
                # If item exists, update its quantity and price
                cursor.execute(""" 
                    UPDATE Inventory 
                    SET quantity = ?, price = ? 
                    WHERE name = ?
                """, (int(quantity), float(price), name))
            else:
                # If item doesn't exist, insert a new record
                cursor.execute(""" 
                    INSERT INTO Inventory (name, quantity, price) 
                    VALUES (?, ?, ?)
                """, (name, int(quantity), float(price)))
            
            self.conn.commit()
            self.item_name_var.set("")
            self.item_quantity_var.set("")
            self.item_price_var.set("")
            self.refresh_inventory()
            self.refresh_products()  # Refresh products to update buildable units
        except sqlite3.IntegrityError as e:
            messagebox.showerror("Integrity Error", str(e))
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))

    def delete_selected_item(self):
        """
        Delete the selected inventory item.
        """
        selected = self.inventory_tree.selection()
        if not selected:
            messagebox.showerror("Error", "No item selected")
            return
    
        # Use the second column (index 1) which contains the actual item_id
        item_id = self.inventory_tree.item(selected)["values"][1]

        if messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete this item?"):
            try:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM Inventory WHERE item_id=?", (item_id,))
                self.conn.commit()

            # Refresh the inventory screen immediately after deletion
                self.refresh_inventory()
                self.refresh_products()  # Refresh products to update buildable units
            except sqlite3.Error as e:
                messagebox.showerror("Database Error", str(e))

    def refresh_inventory(self):
        """
        Refresh the inventory tree view with sequential numbering.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM Inventory ORDER BY item_id")
        rows = cursor.fetchall()
    
        # Clear existing items in the treeview
        self.inventory_tree.delete(*self.inventory_tree.get_children())
    
        # Insert rows with sequential numbering
        for index, row in enumerate(rows, 1):
            # Create a new tuple with the sequential number as the first element
            displayed_row = (index,) + row
            self.inventory_tree.insert("", "end", values=displayed_row)

    def show_add_product_popup(self):
        """
        Show a pop-up window for adding a product.
        """
        popup = Toplevel(self.root)
        popup.title("Add Product")
        popup.geometry("600x500")

        Label(popup, text="Product Name").pack(pady=5)
        product_name_var = StringVar()
        Entry(popup, textvariable=product_name_var).pack(pady=5)

        Label(popup, text="Items Required").pack(pady=10)

        canvas = Canvas(popup, width=550)
        scroll_y = ttk.Scrollbar(popup, orient="vertical", command=canvas.yview)
        scroll_frame = Frame(canvas)
        canvas.create_window(0, 0, anchor="nw", window=scroll_frame)
        canvas.configure(yscrollcommand=scroll_y.set)

        canvas.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

        item_requirements = {}

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM Inventory")
        inventory_items = cursor.fetchall()

        for item_id, name, quantity, price in inventory_items:
            frame = ttk.Frame(scroll_frame)
            frame.pack(pady=2, fill="x", expand=True)
            Label(frame, text=f"{name} (Available: {quantity}, Price: {price:.2f})").pack(side="left")
            req_var = IntVar(value=0)
            Spinbox(frame, from_=0, to=quantity, textvariable=req_var, width=5).pack(side="right")
            item_requirements[item_id] = req_var

        def add_product():
            name = product_name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "Product name is required.")
                return

            try:
                cursor.execute("INSERT INTO Products (name) VALUES (?)", (name,))
                product_id = cursor.lastrowid

                for item_id, req_var in item_requirements.items():
                    if req_var.get() > 0:
                        cursor.execute("INSERT INTO ProductRequirements (product_id, item_id, required_quantity) VALUES (?, ?, ?)",
                                       (product_id, item_id, req_var.get()))
                self.conn.commit()
                popup.destroy()
                self.refresh_products()
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", "A product with this name already exists.")
            except sqlite3.Error as e:
                messagebox.showerror("Database Error", str(e))

        Button(popup, text="Add Product", command=add_product).pack(pady=20)

        scroll_frame.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

    def refresh_products(self):
        """
        Refresh the product tree view with max buildable units.
        """
        cursor = self.conn.cursor()
        cursor.execute(''' 
            SELECT 
                p.product_id, 
                p.name, 
                FLOOR(MIN(IFNULL(i.quantity / pr.required_quantity, 0))) AS units 
            FROM 
                Products p
                LEFT JOIN ProductRequirements pr ON p.product_id = pr.product_id
                LEFT JOIN Inventory i ON pr.item_id = i.item_id
            GROUP BY 
                p.product_id, p.name
        ''')
        rows = cursor.fetchall()
        self.product_tree.delete(*self.product_tree.get_children())
        for row in rows:
            self.product_tree.insert("", "end", values=row)

    def delete_selected_product(self):
        """
        Delete the selected product and its requirements.
        """
        selected = self.product_tree.selection()
        if not selected:
            messagebox.showerror("Error", "No product selected")
            return
        product_id = self.product_tree.item(selected)["values"][0]

        # Debug print the full selected item details
        print("Selected Product Details:", self.product_tree.item(selected))
        print(f"Attempting to delete product with ID: {product_id}")

        if messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete this product?"):
            try:
                cursor = self.conn.cursor()
                
                # Debug: First check if the product exists
                cursor.execute("SELECT * FROM Products WHERE product_id=?", (product_id,))
                existing_product = cursor.fetchone()
                print(f"Existing product: {existing_product}")
                
                # Delete the product
                cursor.execute("DELETE FROM Products WHERE product_id=?", (product_id,))
                deleted_rows = cursor.rowcount
                print(f"Rows deleted: {deleted_rows}")
                
                # Note: Foreign key CASCADE will automatically delete related requirements
                self.conn.commit()
                self.refresh_products()
            except sqlite3.Error as e:
                print(f"Deletion Error: {e}")
                messagebox.showerror("Database Error", str(e))

    def view_product_details(self):
        """
        View detailed requirements for the selected product.
        """
        selected = self.product_tree.selection()
        if not selected:
            messagebox.showerror("Error", "No product selected")
            return

        product_id = self.product_tree.item(selected)["values"][0]
        product_name = self.product_tree.item(selected)["values"][1]

        # Create details popup
        details_popup = Toplevel(self.root)
        details_popup.title(f"Product Details: {product_name}")
        details_popup.geometry("500x400")

        # Fetch product requirements
        cursor = self.conn.cursor()
        cursor.execute(''' 
            SELECT 
                i.name, 
                pr.required_quantity, 
                i.quantity AS available_quantity 
            FROM 
                ProductRequirements pr 
                JOIN Inventory i ON pr.item_id = i.item_id 
            WHERE 
                pr.product_id = ?
        ''', (product_id,))
        requirements = cursor.fetchall()

        # Create treeview for requirements
        req_tree = ttk.Treeview(details_popup, columns=("Item", "Required", "Available"), show="headings")
        req_tree.heading("Item", text="Item Name")
        req_tree.heading("Required", text="Required Quantity")
        req_tree.heading("Available", text="Available Inventory")
        req_tree.pack(padx=10, pady=10, fill='both', expand=True)

        for req in requirements:
            req_tree.insert("", "end", values=req)

    def __del__(self):
        """
        Ensure database connection is closed when the application is closed.
        """
        if hasattr(self, 'conn'):
            self.conn.close()

    def on_close(self):
        """
        Handle the window close event.
        """
        if hasattr(self, 'conn'):
            self.conn.close()  # Ensure the connection is closed before quitting
        self.root.quit()  # Quit the Tkinter mainloop
        self.root.destroy()  # Properly destroy the window


if __name__ == "__main__":
    root = Tk()
    app = InventoryManagementApp(root)
    root.mainloop()
