read_name()
.done(function (data) {
    // Here we put the data into the name of the PoC
    //$('#title_que').val(data);
    document.getElementById('title_que').innerHTML = data;
    //console.log(data);
})

    // Return the API
function read_name()  {
    let ajax_options = {
        type: 'GET',
        url: '/api/region',
        accepts: 'application/json',
        dataType: 'json'
    };
    return $.ajax(ajax_options);
}
        

