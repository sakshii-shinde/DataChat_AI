import os
from dotenv import load_dotenv
import google.generativeai as genai
import re

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

def is_valid_query(question):
    """Basic validation of user input"""
    # Check if question is too short or random characters
    if len(question) < 3:
        return False, "Please ask a more detailed question"
    
    # Check if question contains too many special characters
    special_chars = re.findall(r'[^a-zA-Z0-9\s\?\.,]', question)
    if len(special_chars) > len(question) * 0.3:  # If more than 30% are special chars
        return False, "Your question contains too many special characters. Please rephrase it."
    
    # Check for common SQL injection patterns
    sql_patterns = ['drop', 'delete', 'truncate', ';', '--', 'union']
    if any(pattern in question.lower() for pattern in sql_patterns):
        return False, "Invalid question format. Please ask a natural language question."
    
    return True, ""

def generate_sql_query(question, schema):
    """Generate SQL query using Gemini model"""
    # Format schema for the prompt
    schema_str = ""
    for table_name, table_info in schema.items():
        if table_name not in ['conversation_history', 'sqlite_sequence', 'data']:
            schema_str += f"\nTable: {table_name}\n"
            for col, col_type in zip(table_info['columns'], table_info['types']):
                schema_str += f"  - {col} ({col_type})\n"

    # Generate SQL query using Gemini
    model = genai.GenerativeModel('gemini-2.0-flash')
    sql_prompt = f"""
    Given these database tables and their structure:
    {schema_str}

    Write a SQL query to answer this question: "{question}"

    Analysis Guidelines:
    1. Schema Analysis:
       - Examine table relationships through foreign key columns
       - Understand data types and their meaning:
         * Percentage fields (like discounts) are stored as numbers (e.g., 10 means 10%)
         * Price/monetary fields need decimal precision
         * Dates may need formatting
       - Identify required tables and their relationships

    2. Data Operations:
       - For calculations with percentages:
         * Always divide percentage values by 100
         * Example: 10% should be calculated as value/100
         * Use (1 - discount/100) for discount calculations
       - For monetary calculations:
         * Use ROUND() for consistent decimal places
         * Maintain proper calculation order
       - For counting and aggregations:
         * Choose appropriate functions (SUM, AVG, COUNT)
         * Group results as needed
         * Use LEFT JOIN when counting from reference tables
         * Include all records from main entity
        - For table relationships:
         * ALWAYS use LEFT JOIN from primary entity to preserve all records
         * Start FROM the table containing all records needed (e.g., customers for customer queries)
         * Chain additional LEFT JOINs for related data
         * Use COALESCE/IFNULL for NULL values (e.g., COALESCE(SUM(...), 0))
         * Show zero/empty values for missing data

    3. Query Structure:
      - Start with the main entity table
      - Use LEFT JOIN (not regular JOIN) to preserve all records
      - Apply filters in WHERE clause after joins
      - Group by main entity identifiers
      - Order results meaningfully

    4. Result Formatting:
       - Use clear column aliases
       - Ensure proper ordering
       - Format output for readability
       - Include supporting metrics when:
         * Counting items (show the count)
         * Finding maximums (show the value)
         * Calculating totals (show the total)
         * Comparing data (show relevant measures)
       - Name columns descriptively (e.g., number_of_orders instead of count)
       - For empty results:
         * Return meaningful message instead of empty set
         * Show relevant thresholds or criteria
         * Indicate why no results were found
       - Include all relevant information in results

    Generate a focused SQL query that provides complete information to answer the question.
    Return only the SQL query, no explanations.
    """

    response = model.generate_content(sql_prompt)
    sql_query = response.text.strip()
    
    # Clean the SQL query
    sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
    return sql_query

def generate_explanation(question, sql_query, results):
    """Generate explanation for query results using Gemini model"""
    model = genai.GenerativeModel('gemini-2.0-flash')
    explanation_prompt = f"""
    Based on the original question: "{question}"

    And the SQL query used to retrieve the data: {sql_query}
    
    And the result data retrieved: {results}

    Provide a clear analysis that:
    1. Directly answers the question with key insights and findings
    2. Uses proper markdown formatting for better readability:
       - Use bullet points for listing items
       - Use tables for structured data when relevant
       - Use bold and italics for emphasis
    3. Formats numbers appropriately:
       - Currency with ₹ and two decimal places
       - Percentages with two decimal places
       - Large numbers with comma separators
    4. Provides relevant context or trends when helpful
    
    Keep the focus on answering the user's question clearly and concisely.
    Only mention SQL or technical details if there's a specific issue that affects the results.
    """
    
    explanation = model.generate_content(explanation_prompt).text
    return explanation

def format_results(results):
    """Format numeric values in results"""
    formatted_results = []
    for row in results:
        formatted_row = {}
        for key, value in row.items():
            if isinstance(value, (int, float)):
                key_lower = key.lower()
                if ('price' in key_lower or 
                    'amount' in key_lower or 
                    'sales' in key_lower or
                    'revenue' in key_lower or 
                    'spent' in key_lower or 
                    'cost' in key_lower):
                    formatted_row[key] = f"₹{value:.2f}"
                else:
                    formatted_row[key] = value
            else:
                formatted_row[key] = value
        formatted_results.append(formatted_row)
    return formatted_results 