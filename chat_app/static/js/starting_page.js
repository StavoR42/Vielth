function save_channel_name() {
    var channel_name = $('#channel_name').val();
    $.ajax({
        url: '/save_channel_name/',
        type: 'POST',
        data: {
            'csrfmiddlewaretoken': $('input[name=csrfmiddlewaretoken]').val(),
            'channel_name': channel_name,
        },
        dataType: 'json',
        success: function (response) {
            var status = response['status'],
                message = response['message'];

            if (status === 'error') {
                alert(message);
            }
        }
    })
}