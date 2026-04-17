
      // ---------------- Capture the CSRF token from request header ----------------
      function getCSRFToken() {
        let csrfToken = null;
        const cookies = document.cookie.split(';');
        cookies.forEach(cookie => {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                csrfToken = value;
            }
        });
        return csrfToken;
    }


    // ---------------- Debounce function ----------------
    function debounce(func, wait) {
        let timeout;
        return function (...args) {
            const context = this;
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(context, args), wait);
        };
    }

    // Updated event handler with debounce
    const initializeValidationDebounced = debounce(() => {
        initializeFormValidation(); // existing validation logic
    }, 300); // 300ms debounce



    // ----------------Initialize form validation --------------------
    function initializeFormValidation() {
        const form = document.getElementById('form-container');
        const uploadInput = document.getElementById('upload_input');
        const requiredFields = Array.from(form.querySelectorAll('.form-group input, .form-group select'));
    
        function checkFields() {
            const allFilled = requiredFields.every(field => field.value.trim() !== "");
            uploadInput.disabled = !allFilled;
        }
    
        requiredFields.forEach(field => {
            field.addEventListener('input', checkFields);
            field.addEventListener('change', checkFields);
        });
    
        checkFields(); // Initial check
    }


// ---------------- Haldle project ID selection -----------------------------
function handleProjectIDSelection() {
    $(document).on('change', '#id_proj_id', function () {
        let projectId = $(this).val();
        if (projectId) {
            $('#form-container').html('<p>Loading...</p>');
            $.ajax({
                url: '/edit-project-data/' + projectId + '/',
                success: function (data) {
                    $('#form-container').html(data.form_html);
                    initializeFormValidation(); // Reinitialize validation
                },
                error: function (xhr, status, error) {
                    console.error("AJAX Error:", status, error);
                }
            });
        }
    });
}

$(document).ready(function () {
    initializeFormValidation();
    handleProjectIDSelection();
});


//  SHow Toasts
function showToast(message, type) {
    let toastElement = $('#toast_id');
    let toastBody = toastElement.find('.toast-body');

    // Hide the previous toast
    toastElement.toast('hide');

    // Remove old class
    toastElement.removeClass('bg-success bg-info bg-danger text-white');

    // Update toast body content and type
    toastBody.text(message);
    toastBody.attr('data-message-type', type);

    // Style the toast based on type
    if (type === 'success') {
        toastElement.addClass('bg-success text-white');
    } else if (type === 'info') {
        toastElement.addClass('bg-info text-white');
    } else if (type === 'error') {
        toastElement.addClass('bg-danger text-white');
    }

    // Show the toast
    toastElement.toast({ delay: 6000 }); // Auto-hide delay
    toastElement.toast('show'); // Show the toast
}

// Add event listener to the close button within the toast
$(document).on('click', '#toast_id .close', function () {
    $('#toast_id').toast('hide'); // Hide the toast when the close button is clicked
 });

 
/**
 * Handle AJAX errors consistently.
 * @param {Object} xhr - The XHR object.
*/
function handleErrorResponse(xhr) {
    let errorMessage = "An unexpected error occurred."; // Default error message
    try {
        let reader = new FileReader();
        reader.onload = function () {
            try {
                let jsonResponse = JSON.parse(reader.result);
                if (jsonResponse.error) {
                    errorMessage = jsonResponse.error;
                }
                showToast(errorMessage, "error");
            } catch (e) {
                showToast("Failed to parse error response.", "error");
            }
        };
        reader.readAsText(xhr.response); // Attempt to parse response as JSON
    } catch (e) {
        showToast(errorMessage, "error");
    }
}



//       // AJAX for Upload
//       $('#upload_input').change(function () {
//           let formData = new FormData();
//           formData.append('file', this.files[0]);
  
//           $.ajax({
//               url: "{% url 'upload_input_file' %}",
//               type: 'POST',
//               headers: {
//                 'X-CSRFToken': getCSRFToken() // Attach the CSRF token
//             },
//               data: formData,
//               processData: false,
//               contentType: false,
//               success: function (response) {
//                 showToast("File uploaded and processed successfully.", "success");             
//               },
//               error: function (xhr) {
//                 showToast(xhr.responseJSON.error, "error");
//               }
//           });
//       });
  
//   // Download Template
//       $(document).ready(function (){ 
//       $('#download_template').click(function () {
//           window.location.href = "{% url 'download_template_file' %}";          
//           showToast("Template download has started.", "success");      
//       });
//     });
  

