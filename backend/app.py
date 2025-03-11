from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import os
import google.generativeai as genai
from dotenv import load_dotenv
from database import (
    create_table_from_file, 
    init_database, 
    init_db, 
    get_table_schema,
    remove_table
)
from gemini_service import is_valid_query, generate_sql_query, generate_explanation, format_results
import traceback
from werkzeug.utils import secure_filename

load_dotenv()
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

app = Flask(__name__)

# Configure CORS to allow requests from your frontend
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:3000"],  # Your frontend URL
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"],
    }
})

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        "status": "Server is running",
        "app": "DataChat AI"
    }), 200

@app.route('/upload/csv', methods=['POST'])
def upload_csv():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if file:
            filename = secure_filename(file.filename)
            print(f"Received file: {filename}")
            
            # Create DataFrame from CSV
            df = pd.read_csv(file)
            
            # Get table name from filename (without extension)
            table_name = os.path.splitext(filename)[0]
            
            # Create table in database
            create_table_from_file(df, table_name)
            
            return jsonify({
                'message': 'File uploaded successfully',
                'table': table_name
            })
            
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/remove/<filename>', methods=['POST'])
def remove_file(filename):
    try:
        table_name = os.path.splitext(filename)[0]
        remove_table(table_name)
        schema = get_table_schema()
        return jsonify({'message': 'File removed successfully', 'schema': schema})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/query', methods=['POST'])
def process_query():
    try:
        data = request.json
        if not data or 'question' not in data:
            return jsonify({
                'error': 'No question provided',
                'suggestion': 'Please provide a question to analyze'
            }), 400

        question = data['question']
        print(f"Processing question: {question}")

        # Validate the question first
        is_valid, error_message = is_valid_query(question)
        if not is_valid:
            return jsonify({
                'error': error_message,
                'suggestion': "Try asking something like: 'What are the total sales?' or 'Show me orders from January 2024'"
            }), 400

        # Get current schema with error checking
        try:
            schema = get_table_schema()
            print("Schema retrieved:", schema)
        except Exception as e:
            print(f"Error getting schema: {str(e)}")
            return jsonify({
                'error': 'Database error',
                'suggestion': 'There was an error accessing the database'
            }), 500

        if not schema:
            return jsonify({
                'error': 'No tables found in database',
                'suggestion': 'Please upload some data files first'
            }), 400

        try:
            # Generate SQL query
            sql_query = generate_sql_query(question, schema)
            print("Generated SQL query:", sql_query)

            # Execute the query
            with init_db() as conn:
                df = pd.read_sql_query(sql_query, conn)
                print("Query executed successfully, row count:", len(df))
                
            if df.empty:
                return jsonify({
                    'error': 'No results found',
                    'sql_query': sql_query,
                    'suggestion': 'Try modifying your question'
                }), 404

            # Format results for explanation
            results = df.to_dict('records')
            
            # Generate explanation
            explanation = generate_explanation(question, sql_query, results)
            
            # Format results
            formatted_results = format_results(results)
            
            return jsonify({
                'sql_query': sql_query,
                'data': formatted_results,
                'explanation': explanation,
                'row_count': len(df)
            })

        except Exception as e:
            print(f"SQL execution error: {str(e)}")
            return jsonify({
                'error': 'Error executing the query',
                'sql_query': sql_query,
                'suggestion': 'There might be an issue with the generated SQL query'
            }), 400

    except Exception as e:
        print(f"General error in process_query: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'error': 'Failed to process your question',
            'suggestion': 'Please try asking in a different way or check your question for typos'
        }), 400

if __name__ == '__main__':
    # Initialize database
    init_database()
    # Explicitly bind to all interfaces
    app.run(host='127.0.0.1', port=5000, debug=True) 