from flask import Flask,render_template,request,redirect,session,url_for,flash
import sqlite3
from functools import wraps
app=Flask(__name__); app.secret_key='easyshop-pro-secret'; DB='shop.db'
def db():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init_db():
 c=db(); c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,email TEXT UNIQUE,password TEXT,is_admin INTEGER DEFAULT 0);CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,price REAL,old_price REAL,category TEXT,description TEXT,image TEXT,stock INTEGER,rating REAL,featured INTEGER);CREATE TABLE IF NOT EXISTS wishlist(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,product_id INTEGER,UNIQUE(user_id,product_id));CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,total REAL,address TEXT,status TEXT DEFAULT 'Placed',created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);CREATE TABLE IF NOT EXISTS order_items(id INTEGER PRIMARY KEY AUTOINCREMENT,order_id INTEGER,product_id INTEGER,quantity INTEGER,price REAL);CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,product_id INTEGER,rating INTEGER,comment TEXT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
 if c.execute('SELECT COUNT(*) FROM products').fetchone()[0]==0:
  ps=[('Laptop',69999,79999,'Electronics','Laptop for study and work','https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=900',8,4.8,1),('Headphones',2499,3499,'Electronics','Wireless headphones','https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=900',18,4.6,1),('Smart Watch',3299,4999,'Electronics','Fitness smart watch','https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=900',14,4.5,1),('Backpack',1399,1999,'Fashion','College backpack','https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=900',25,4.7,1),('T-Shirt',699,999,'Fashion','Cotton T-shirt','https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=900',35,4.4,0),('Running Shoes',2799,3999,'Fashion','Casual running shoes','https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=900',16,4.7,1),('Coffee Mug',399,599,'Home','Ceramic coffee mug','https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?w=900',40,4.3,0),('Desk Lamp',1199,1699,'Home','Modern LED desk lamp','https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=900',20,4.5,0)]
  c.executemany('INSERT INTO products(name,price,old_price,category,description,image,stock,rating,featured) VALUES(?,?,?,?,?,?,?,?,?)',ps)
 if c.execute('SELECT COUNT(*) FROM users').fetchone()[0]==0:c.execute('INSERT INTO users(name,email,password,is_admin) VALUES(?,?,?,1)',('Admin','admin@easyshop.com','admin123'))
 c.commit();c.close()
def req(f):
 @wraps(f)
 def w(*a,**k):
  if 'user_id' not in session:return redirect(url_for('login'))
  return f(*a,**k)
 return w
def admin(f):
 @wraps(f)
 def w(*a,**k):
  if not session.get('is_admin'):return redirect(url_for('home'))
  return f(*a,**k)
 return w
def items():
 c=db(); out=[]; total=0
 for pid,q in session.get('cart',{}).items():
  p=c.execute('SELECT * FROM products WHERE id=?',(pid,)).fetchone()
  if p and p['stock']:
   q=min(q,p['stock']); sub=p['price']*q;out.append((p,q,sub));total+=sub
 c.close();return out,total
@app.context_processor
def ctx():return {'cart_count':sum(session.get('cart',{}).values())}
@app.route('/')
def home():
 q=request.args.get('q','');cat=request.args.get('category','');sort=request.args.get('sort','featured');c=db();sql='SELECT * FROM products WHERE 1=1';ps=[]
 if q:sql+=' AND (name LIKE ? OR description LIKE ? OR category LIKE ?)';ps += [f'%{q}%',f'%{q}%',f'%{q}%']
 if cat:sql+=' AND category=?';ps.append(cat)
 order={'featured':'featured DESC,rating DESC','price_low':'price ASC','price_high':'price DESC','rating':'rating DESC'}.get(sort,'featured DESC')
 products=c.execute(sql+' ORDER BY '+order,ps).fetchall();cats=c.execute('SELECT DISTINCT category FROM products').fetchall();featured=c.execute('SELECT * FROM products WHERE featured=1 ORDER BY rating DESC LIMIT 4').fetchall();c.close();return render_template('index.html',products=products,featured=featured,categories=cats,q=q,category=cat,sort=sort)
@app.route('/product/<int:pid>')
def product(pid):
 c=db();p=c.execute('SELECT * FROM products WHERE id=?',(pid,)).fetchone();reviews=c.execute('SELECT reviews.*,users.name FROM reviews JOIN users ON users.id=reviews.user_id WHERE product_id=? ORDER BY reviews.id DESC',(pid,)).fetchall();related=c.execute('SELECT * FROM products WHERE category=(SELECT category FROM products WHERE id=?) AND id!=? LIMIT 4',(pid,pid)).fetchall();c.close();return render_template('product.html',p=p,reviews=reviews,related=related)
@app.route('/register',methods=['GET','POST'])
def register():
 if request.method=='POST':
  c=db()
  try:c.execute('INSERT INTO users(name,email,password) VALUES(?,?,?)',(request.form['name'],request.form['email'].lower(),request.form['password']));c.commit()
  except sqlite3.IntegrityError:c.close();return render_template('register.html',error='Email already registered.')
  c.close();return redirect('/login')
 return render_template('register.html')
@app.route('/login',methods=['GET','POST'])
def login():
 if request.method=='POST':
  c=db();u=c.execute('SELECT * FROM users WHERE email=? AND password=?',(request.form['email'].lower(),request.form['password'])).fetchone();c.close()
  if u:session.update(user_id=u['id'],name=u['name'],is_admin=bool(u['is_admin']));return redirect('/')
  return render_template('login.html',error='Invalid login.')
 return render_template('login.html')
@app.route('/logout')
def logout():session.clear();return redirect('/')
@app.route('/add/<int:pid>')
def add(pid):
 cart=session.get('cart',{});k=str(pid);cart[k]=cart.get(k,0)+1;session['cart']=cart;return redirect(request.referrer or '/')
@app.route('/cart')
def cart():i,t=items();return render_template('cart.html',items=i,total=t)
@app.route('/update/<int:pid>',methods=['POST'])
def update(pid):n=max(1,int(request.form['quantity']));cart=session.get('cart',{});cart[str(pid)]=n;session['cart']=cart;return redirect('/cart')
@app.route('/remove/<int:pid>')
def remove(pid):cart=session.get('cart',{});cart.pop(str(pid),None);session['cart']=cart;return redirect('/cart')
@app.route('/wishlist')
@req
def wishlist():
 c=db();p=c.execute('SELECT products.* FROM products JOIN wishlist ON wishlist.product_id=products.id WHERE wishlist.user_id=?',(session['user_id'],)).fetchall();c.close();return render_template('wishlist.html',products=p)
@app.route('/wishlist/toggle/<int:pid>')
@req
def toggle(pid):
 c=db();x=c.execute('SELECT id FROM wishlist WHERE user_id=? AND product_id=?',(session['user_id'],pid)).fetchone();
 if x:c.execute('DELETE FROM wishlist WHERE id=?',(x['id'],))
 else:c.execute('INSERT OR IGNORE INTO wishlist(user_id,product_id) VALUES(?,?)',(session['user_id'],pid))
 c.commit();c.close();return redirect(request.referrer or '/')
@app.route('/checkout',methods=['GET','POST'])
@req
def checkout():
 i,t=items()
 if request.method=='POST':
  c=db();o=c.execute('INSERT INTO orders(user_id,total,address) VALUES(?,?,?)',(session['user_id'],t,request.form['address']));oid=o.lastrowid
  for p,q,s in i:c.execute('INSERT INTO order_items(order_id,product_id,quantity,price) VALUES(?,?,?,?)',(oid,p['id'],q,p['price']));c.execute('UPDATE products SET stock=stock-? WHERE id=?',(q,p['id']))
  c.commit();c.close();session['cart']={};return redirect('/orders')
 return render_template('checkout.html',items=i,total=t)
@app.route('/orders')
@req
def orders():c=db();o=c.execute('SELECT * FROM orders WHERE user_id=? ORDER BY id DESC',(session['user_id'],)).fetchall();c.close();return render_template('orders.html',orders=o)
@app.route('/review/<int:pid>',methods=['POST'])
@req
def review(pid):
 c=db();c.execute('INSERT INTO reviews(user_id,product_id,rating,comment) VALUES(?,?,?,?)',(session['user_id'],pid,int(request.form['rating']),request.form['comment']));c.commit();c.close();return redirect('/product/'+str(pid))
@app.route('/profile')
@req
def profile():c=db();u=c.execute('SELECT * FROM users WHERE id=?',(session['user_id'],)).fetchone();c.close();return render_template('profile.html',user=u)
@app.route('/admin')
@admin
def adm():c=db();p=c.execute('SELECT * FROM products').fetchall();o=c.execute('SELECT orders.*,users.name FROM orders JOIN users ON users.id=orders.user_id ORDER BY orders.id DESC').fetchall();c.close();return render_template('admin.html',products=p,orders=o)
@app.route('/admin/add',methods=['POST'])
@admin
def addp():
 c=db();c.execute('INSERT INTO products(name,price,old_price,category,description,image,stock,rating,featured) VALUES(?,?,?,?,?,?,?,?,?)',(request.form['name'],float(request.form['price']),float(request.form.get('old_price') or 0),request.form['category'],request.form['description'],request.form['image'],int(request.form['stock']),4.5,int('featured' in request.form)));c.commit();c.close();return redirect('/admin')
@app.route('/admin/delete/<int:pid>')
@admin
def delp(pid):c=db();c.execute('DELETE FROM products WHERE id=?',(pid,));c.commit();c.close();return redirect('/admin')
@app.route('/admin/status/<int:oid>',methods=['POST'])
@admin
def status(oid):c=db();c.execute('UPDATE orders SET status=? WHERE id=?',(request.form['status'],oid));c.commit();c.close();return redirect('/admin')
if __name__=='__main__':init_db();app.run(debug=True)
