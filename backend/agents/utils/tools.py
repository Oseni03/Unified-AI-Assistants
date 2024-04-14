from simple_salesforce import Salesforce
from langchain.tools import tool


class SalesForceTools:
    def __init__(self, username, password, security_token, instance, session_id='') -> None:
        self.sf = Salesforce(instance=instance, session_id=session_id)
        self.sf = Salesforce(username=username, password=password, security_token=security_token)

    @tool
    def search_knowledge(self, query: str) -> str:
        """
        Searches Salesforce Knowledge articles for a given query using SOSL, within the LangChain framework.

        Parameters:
            query (str): The keyword or phrase to search for within Salesforce Knowledge articles.
        
        Returns:
            str: A formatted string containing the titles, questions, and URLs of the found articles, dynamically constructed based on the Salesforce instance.
        """
        # Assuming 'sf' Salesforce connection object is initialized and accessible globally

        print (f"Searching Salesforce Knowledge for: {query}")
        # Format the SOSL search string with the search term enclosed in braces
        search_string = "FIND {{{0}}} IN ALL FIELDS RETURNING Knowledge__kav(Id, Title, Question__c, Answer__c, UrlName)".format(query)
        print (f"search_string: {search_string}")
        search_result = self.sf.search(search_string)
        

        
        # Initialize an empty list to store formatted article details
        articles_details = []

        # Dynamically construct the base URL from the Salesforce instance URL
        base_url = self.sf.base_url.split('/services')[0]

        # Process search results
        for article in search_result['searchRecords']:
            # Dynamically construct the URL for the article using the Salesforce instance URL
            article_id = article['Id']
            article_url = f"{base_url}/lightning/r/Knowledge__kav/{article_id}/view"
            article_details = f"Title: {article['Title']}, Question: {article['Question__c']}, AnswerL:{article['Answer__c']}, URL: {article_url}"
            articles_details.append(article_details)

        print(articles_details)

        # Join all article details into a single string to return
        return "\n".join(articles_details)
    
    @tool
    def search_opportunities(self, query: str) -> str:
        """
        Searches Salesforce opportunities for a given query using SOSL, within the LangChain framework.

        Parameters:
            query (str): The keyword or phrase to search for within Salesforce opportunities.
        
        Returns:
            str: A formatted string containing the details of the found opportunities, dynamically constructed based on the Salesforce instance.
        """
        # Assuming 'sf' Salesforce connection object is initialized and accessible globally

        print(f"Searching Salesforce opportunities for: {query}")
        # Format the SOSL search string with the search term enclosed in braces
        search_string = "FIND {{{0}}} IN ALL FIELDS RETURNING Opportunity(Id, Name, CloseDate, Amount, StageName, )".format(query)
        print(f"search_string: {search_string}")
        search_result = self.sf.search(search_string)

        # Initialize an empty list to store formatted opportunity details
        opportunities_details = []

        # Process search results
        for opportunity in search_result['searchRecords']:
            # Construct opportunity details
            opportunity_details = f"Opportunity: {opportunity['Name']}, Close Date: {opportunity['CloseDate']}, Amount: {opportunity['Amount']}, Stage: {opportunity['StageName']},"
            opportunities_details.append(opportunity_details)

        print(opportunities_details)

        # Join all opportunity details into a single string to return
        return "\n".join(opportunities_details)

    @tool
    def create_case(self, subject: str, description: str) -> str:
        """
        Creates a case record in Salesforce using the provided subject and description.

        Parameters:
            subject (str): The subject of the case.
            description (str): The description of the case.
        
        Returns:
            str: A confirmation message indicating whether the case was successfully created or not, along with a link to the created case.
        """
        try:
            # Create a dictionary with case details
            case_details = {
                'Subject': subject,
                'Description': description,
                'Origin': 'Web'  # Set the default case origin to "Web"
            }
            
            # Create the case record in Salesforce
            new_case = self.sf.Case.create(case_details)
            
            # Extract the Case Id from the newly created case record
            case_id = new_case['id']
            
            # Construct the link to the created case
            case_link = f"{self.sf.base_url}/lightning/r/Case/{case_id}/view"
            
            # Return success message along with the link to the created case
            return f"Case created successfully. Case Link: {case_link}"
        
        except Exception as e:
            # Return error message if case creation fails
            return f"Error creating case: {str(e)}"


    @tool
    def search_account_summary(self, account_name: str) -> str:
        """
        Searches for Opportunities, Contacts, and Cases associated with the provided Account name.

        Parameters:
            account_name (str): The name of the Account to search for.

        Returns:
            str: A formatted summary containing information about Opportunities, Contacts, and Cases.
        """
        try:
            # Step 1: Search for the Account based on the provided name
            search_result = self.sf.query(f"SELECT Id, Name FROM Account WHERE Name LIKE '%{account_name}%' LIMIT 1")
            if search_result['totalSize'] == 0:
                return f"No Account found with a similar name to '{account_name}'."

            # Extract Account Id from the search result
            account_id = search_result['records'][0]['Id']

            # Step 2: Retrieve associated Opportunities, Contacts, and Cases
            opportunities = self.sf.query_all(f"SELECT Id, Name, Amount, StageName FROM Opportunity WHERE AccountId = '{account_id}'")
            contacts = self.sf.query_all(f"SELECT Id, Name FROM Contact WHERE AccountId = '{account_id}'")
            cases = self.sf.query_all(f"SELECT Id, CaseNumber, Subject, Description FROM Case WHERE AccountId = '{account_id}'")

            # Format the summary
            summary = f"Account Summary for '{account_name}':\n\n"

            # Add information about Opportunities
            if opportunities['totalSize'] > 0:
                summary += "Opportunities:\n"
                for opp in opportunities['records']:
                    summary += f"- Opportunity: {opp['Name']}, Amount: {opp.get('Amount', 'N/A')}, Stage: {opp.get('StageName', 'N/A')}\n"
            else:
                summary += "No Opportunities found.\n"

            # Add information about Contacts
            if contacts['totalSize'] > 0:
                summary += "\nContacts:\n"
                for contact in contacts['records']:
                    summary += f"- Contact: {contact['Name']}\n"
            else:
                summary += "No Contacts found.\n"

            # Add information about Cases
            if cases['totalSize'] > 0:
                summary += "\nCases:\n"
                for case in cases['records']:
                    summary += f"- Case Number: {case['CaseNumber']}, Subject: {case.get('Subject', 'N/A')}, Description: {case.get('Description', 'N/A')}\n"
            else:
                summary += "No Cases found.\n"

            return summary

        except Exception as e:
            return f"Error searching for Account summary: {str(e)}"
