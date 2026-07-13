define(['jquery'], function($) {
    return {
        init: function() {
            $('#tutor-ai-send').on('click', function() {
                var message = $('#tutor-ai-input').val().trim();
                if (message === '') return;

                // Afficher le message de l'étudiant
                $('#tutor-ai-messages').append(
                    '<div class="tutor-ai-bubble user">' + message + '</div>'
                );
                $('#tutor-ai-input').val('');

                // Afficher indicateur de chargement
                $('#tutor-ai-messages').append(
                    '<div class="tutor-ai-bubble bot" id="loading">...</div>'
                );

                // Appel au microservice (à configurer plus tard)
                $.ajax({
                    url: '/blocks/tutor_ai/ask.php',
                    method: 'POST',
                    data: { question: message },
                    success: function(response) {
                        $('#loading').remove();
                        $('#tutor-ai-messages').append(
                            '<div class="tutor-ai-bubble bot">' + response + '</div>'
                        );
                    },
                    error: function() {
                        $('#loading').remove();
                        $('#tutor-ai-messages').append(
                            '<div class="tutor-ai-bubble bot">Erreur de connexion.</div>'
                        );
                    }
                });
            });

            // Envoyer avec la touche Enter
            $('#tutor-ai-input').on('keypress', function(e) {
                if (e.which === 13) {
                    $('#tutor-ai-send').click();
                }
            });
        }
    };
});