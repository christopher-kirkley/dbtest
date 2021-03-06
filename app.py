from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy

from flask_migrate import Migrate
import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://ck:foof@localhost:5432/test'

db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)

def create_tables():
    from models import Pet
    db.create_all()

@app.route('/')
@app.route('/index')
def index():

    return '<h1>hello</h1>'


@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':
        name = request.form['name']
        user = User(name=name)
        db.session.add(user)
        db.session.commit()
        db.engine.execute(f"CREATE SCHEMA {name}") # Create Schema for username
        db.engine.execute(f"SET search_path TO {name}")

        """This is where we can list all the classes, or import all models.
        This set_path needs to be also addressed on user login page."""
        from models import Noob
        db.engine.execution_options(schema_translate_map={'name': name})

        db.create_all() # Create the table

        return 'success'

    return render_template('register.html')


imported_statements = defaultdict(list)

class Statement:
    def __init__(self, file):
        self.file = file
    
    def create_df(self):
        self.df = pd.read_csv(self.file, encoding=self.encoding)
        self.columns_for_db = ['id', 'distributor', 'date', 'order_id', 'upc_id', 'isrc_id', 'version_id', 'catalog_id',
                        'album_name', 'track_name', 'quantity', 'label_net', 'customer', 'city', 'region', 'country',
                        'type', 'class', 'product', 'variant']

    def insert_to_db(self):
        pass    

class BandcampStatement(Statement):
    def __init__(self, file):
        super().__init__(file)
        self.name = 'bandcamp'
        self.encoding = 'utf-16'

    def clean(self):

        """Clean data."""
        self.df.drop(self.df[self.df['item type'] == 'payout'].index, inplace=True)
        types_to_change = ['refund', 'reversal']
        self.df.loc[self.df['item type'].isin(types_to_change), 'net amount'] = self.df['change to payout balance']
        self.df.loc[self.df['item type']=='album', 'item type'] = 'digital'
        self.df.loc[self.df['item type']=='track', 'item type'] = 'digital'
        self.df.loc[self.df['item type']=='package', 'item type'] = 'physical'
        
        """using numpy"""
        #self.df['net amount'] = np.where(self.df['item type']=='reversal', self.df['change to payout balance'], self.df['net amount'])
        #self.df['net amount'] = np.where(self.df['item type']=='refund', self.df['change to payout balance'], self.df['net amount'])
        #self.df['item type'] = np.where(self.df['item type'] == 'album', 'digital', 'physical')
        self.df['sku'] = np.where(self.df['item type']=='digital', self.df['catalog number']+'digi', self.df['sku'])
        
        """Reformat strings."""
        self.df['date'] = pd.to_datetime(self.df['date'])
        self.df['date'] = self.df['date'].dt.strftime('%Y-%m-%d')

        """Remap columns, drop extraneous, add missing."""
        self.df.rename(columns={'date':'date',
                                'bandcamp transaction':'order_id',
                                'upc':'upc_id',
                                'isrc':'isrc_id',
                                'sku':'version_id',
                                'catalog number':'catalog_id',
                                'quantity':'quantity',
                                'net amount':'net',
                                'city':'city',
                                'region/state':'region',
                                'country':'_country',
                                'country code':'country',
                                'item type':'type',
                                },
                                inplace=True)
        self.df = self.df.reindex(columns=self.columns_for_db) # Add needed columns, drop extraneous columns
        self.df.to_sql('pending', con=db.engine, if_exists = 'append')
        


        
class ShopifyStatement(Statement):
    def __init__(self, file):
        super().__init__(file)
        self.name = 'shopify'
        self.encoding = 'utf-8'

class StatementFactory:
    def get_statement(file, type):
        if type == 'bandcamp_statement':
            return BandcampStatement(file)
        if type == 'shopify_statement':
            return ShopifyStatement(file)
        if type == 'sd_statement':
            return SDStatement(file)

@app.route('/import_income', methods=['GET', 'POST'])
def import_income():
    
    if request.method == 'POST':
        if 'file' not in request.files:
            return 'no file'
        file = request.files['file']
        filename = file.filename
        if file.filename == '':
            return 'no selected file'
        if file:
            if any(file.filename in list for list in imported_statements.values()) == True:
                return "already imported!"
            statement_type = request.form.get('statement_type')
            statement = StatementFactory.get_statement(file, statement_type)
            statement.create_df()
            """clean and import into db"""
        imported_statements[statement.name].append(file.filename)            

    return render_template('import_income.html', imported_statements=imported_statements)


"""Conditional to run the application."""
if __name__ == '__main__':
    app.run(debug=True)

