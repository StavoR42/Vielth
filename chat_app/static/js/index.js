$(document).ready(function() {
    var chatSocket = new WebSocket('ws://' + window.location.host + '/ws/twitch-chat/');

    chatSocket.onmessage = function(e) {
        debugger;
        var data = JSON.parse(JSON.parse(e.data)['message']);
        var datetime = data['datetime'];
        var username = data['username'];
        var message = data['message'];
        var $chat = $('#chat');

        $chat.append(
            '<div class="message">' +
            '<span class="time">' + datetime + '</span> ' +
            '<span class="username">' + username + '</span>: ' +
            '<span class="message">' + message + '</span>' +
            '</div>'
        );
    };

    chatSocket.onclose = function(e) {
        console.error('Chat socket closed unexpectedly');
    };

    // document.querySelector('#chat-message-input').focus();
    // document.querySelector('#chat-message-input').onkeyup = function(e) {
    //     if (e.keyCode === 13) {  // enter, return
    //         document.querySelector('#chat-message-submit').click();
    //     }
    // };
    //
    // document.querySelector('#chat-message-submit').onclick = function(e) {
    //     var messageInputDom = document.querySelector('#chat-message-input');
    //     var message = messageInputDom.value;
    //     chatSocket.send(JSON.stringify({
    //         'message': message
    //     }));
    //
    //     messageInputDom.value = '';
    // };
});

