*<!-- * Code Review by Google AI Studio ---------------

**project_data_html.txt:**
    -  Currently there are three buttons with all having same type, it should be changed to make it more meaningful with different actions.
    -  The logic of template download should be different from the main form submission using the same form. We should make separate call for all these      functions. The download button should have download link and should not submit the whole form.
    -  The button Navigate to Input Page, this will be a simple redirect to input page and will have nothing to do with the form submission.
    -  The code is mixing business logic with UI in the javascript, which we will address in next revisions.

**models_py.txt:**
    -  Consider adding indexes where necessary on ForeignKey, or often queried fields to improve performance of db queries.
    -  While it is good to implement __str__ method for debug purpose, for real production code we need to implement more complex object relation handling to understand data structure easily.
    -  For complex models, use proper relations and foreign keys, which we will refine in coming iterations.

**views.py**
    -  The view function is doing a lot of different functionalities, which should be splitted into different functions to manage it effectively.
    -  The handle_project_data function, should not fetch the data from database, and should use Django Form directly to fetch and validate the input fields.
    -  The views should not have any business logic like the processing excel file, rather, it should be done in separate modules.
    -  The views should do only basic data handling, and preparing the data to pass it to the HTML template or the python utils/service functions.
    -  You are missing the logout functionality.
    -  The download_template function is not protected with try..catch block.

**base_html.txt and base_js.txt:**
    -  The debouce function and tab event listener should be moved to a separate file, so that they can be used across different application.
    -  The logic to toggle the side panel is tightly coupled to ID of html elements, which is not good practice and prone to break if the id of elements are  
       hanged.
    -The loading spinner should be added when an ajax call is being made to the server.
    -The javascript code on html pages should have proper error checking and should be modular, so that they can be reused.

**Specific Recommendations**

    Refactor sanitize_input.py:
        Separate the file-level validations (size, extension) from the data-level validations into separate functions.

    Use structured output for reporting errors (e.g., a list of dictionaries).
        Handle all types of specific exceptions and use logger to write exceptions.

    Clean up views.py:
        Keep the core function of views, i.e. to respond to HTTP requests.
        Extract the data processing/cleaning logic and calculation logic to separate utilities/service modules.
        Move view logic to helpers where needed.

    Refactor forms.py
        Remove the default values for the factors and consider defining them either in a dedicated file or using a dictionary or python variables.
        The Form class should only be used to handle UI inputs, not other business logics, which you are currently handling on model class and form initialisation.
        Implement proper Django error handling Implement custom error handlers with logger for better error analysis.
        Focus on modular design : Try to create each logical unit of code as a separate function or a class/module which can be reused in other sections of the application.

    Start with core logic : 
        Focus on implementing the build_sld_json function in thesld_layout.py, which we have discussed in our earlier responses. Once we complete this we can create the client side code to render the diagrams.