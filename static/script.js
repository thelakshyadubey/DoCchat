// Handle file uploads and drag & drop
$(document).ready(function () {
  // Dashboard page functionality
  if ($("#upload-form").length) {
    const dropArea = $("#drop-area");
    const fileInput = $("#file-upload");
    const uploadForm = $("#upload-form");
    const uploadStatus = $("#upload-status");

    // Prevent default drag behaviors
    ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
      dropArea.on(eventName, preventDefaults);
    });

    function preventDefaults(e) {
      e.preventDefault();
      e.stopPropagation();
    }

    function highlight() {
      dropArea.addClass("highlight");
    }

    function unhighlight() {
      dropArea.removeClass("highlight");
    }

    function handleDrop(e) {
      const dt = e.originalEvent.dataTransfer;
      const files = dt.files;
      fileInput[0].files = files;
      handleFiles();
    }

    function handleFiles() {
      const files = fileInput[0].files;
      console.log("Files selected:", files); // Debug
      if (files.length === 0) return;

      const formData = new FormData();
      for (let i = 0; i < files.length; i++) {
        console.log(`Adding file ${i}: ${files[i].name}`); // Debug
        formData.append("file", files[i]);
      }

      console.log("FormData contents:");
      for (let pair of formData.entries()) {
        console.log(pair[0], pair[1]);
      }

      uploadStatus.html(
        '<p>Uploading files... <span class="loading"></span></p>'
      );

      $.ajax({
        url: "/upload",
        type: "POST",
        data: formData,
        processData: false,
        contentType: false,
        success: function (response) {
          if (response.success) {
            uploadStatus.html(
              `<p class="success">Successfully uploaded: ${response.files.join(
                ", "
              )}</p>`
            );
            setTimeout(() => location.reload(), 1500);
          } else {
            uploadStatus.html(
              `<p class="error">Error: ${response.error || "Unknown error"}</p>`
            );
          }
        },
        error: function (xhr) {
          let errorMsg = "Upload failed";
          try {
            const response = JSON.parse(xhr.responseText);
            errorMsg = response.error || errorMsg;
          } catch (e) {
            errorMsg = xhr.statusText || errorMsg;
          }
          uploadStatus.html(`<p class="error">Error: ${errorMsg}</p>`);
          console.error("Upload error:", xhr);
        },
      });
    }

    // Highlight drop area when item is dragged over it
    ["dragenter", "dragover"].forEach((eventName) => {
      dropArea.on(eventName, highlight);
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dropArea.on(eventName, unhighlight);
    });

    // Handle dropped files
    dropArea.on("drop", handleDrop);

    // Handle file selection via button
    fileInput.on("change", handleFiles);

    // Handle form submission
    uploadForm.on("submit", function (e) {
      e.preventDefault();
      if (fileInput[0].files.length > 0) {
        handleFiles();
      }
    });
  }

  // Chat page functionality
  if ($("#chat-box").length) {
    // Verify docIds exists in global scope
    if (typeof docIds === "undefined" || !Array.isArray(docIds)) {
      console.error("docIds not properly initialized!");
      $("#chat-box").append(`
                <div class="error-message">
                    System Error: Document selection failed. Please try again.
                </div>
            `);
      return;
    }

    const chatBox = $("#chat-box");
    const userInput = $("#user-input");
    const sendButton = $("#send-button");

    // Initial bot greeting
    addMessage(
      "Hello! I can answer questions about your selected documents. What would you like to know?",
      "bot"
    );

    function sendMessage() {
      const message = userInput.val().trim();
      if (message === "") return;

      addMessage(message, "user");
      userInput.val("");

      const typingIndicator = $(
        '<div class="chat-message bot-message">Thinking...</div>'
      );
      chatBox.append(typingIndicator);
      chatBox.scrollTop(chatBox[0].scrollHeight);

      $.ajax({
        url: "/api/chat",
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify({
          query: message,
          doc_ids: docIds.map((id) => parseInt(id)),
        }),
        success: function (response) {
          typingIndicator.remove();
          if (response.response) {
            addMessage(response.response, "bot");
          } else {
            const errorMsg =
              response.error || "Sorry, I couldn't process your request.";
            addMessage(errorMsg, "bot");
          }
        },
        error: function (xhr) {
          typingIndicator.remove();
          let errorMsg = "Sorry, there was an error processing your request.";
          try {
            const response = JSON.parse(xhr.responseText);
            errorMsg = response.error || errorMsg;
          } catch (e) {
            console.error("Error parsing error response:", e);
          }
          addMessage(errorMsg, "bot");
        },
      });
    }

    function addMessage(text, sender) {
      const messageClass = sender === "user" ? "user-message" : "bot-message";
      const messageElement = $(
        `<div class="chat-message ${messageClass}">${text}</div>`
      );
      chatBox.append(messageElement);
      chatBox.scrollTop(chatBox[0].scrollHeight);
    }

    // Event listeners
    sendButton.on("click", sendMessage);
    userInput.on("keypress", function (e) {
      if (e.which === 13) {
        sendMessage();
      }
    });
  }
});

// Add this to your existing script.js
// Handle delete buttons
$(document).on("click", ".btn-delete", function () {
  const docId = $(this).data("doc-id");
  const row = $(this).closest("tr");

  if (
    confirm(
      "Are you sure you want to delete this document? This cannot be undone."
    )
  ) {
    $.ajax({
      url: `/delete/${docId}`,
      type: "DELETE",
      success: function (response) {
        if (response.success) {
          row.fadeOut(300, function () {
            $(this).remove();
            if ($("tbody tr").length === 0) {
              $("tbody").append(
                '<tr><td colspan="4">No documents uploaded yet.</td></tr>'
              );
            }
          });
        } else {
          alert("Error: " + (response.error || "Failed to delete document"));
        }
      },
      error: function (xhr) {
        alert("Error: " + (xhr.responseJSON?.error || "Request failed"));
      },
    });
  }
});
