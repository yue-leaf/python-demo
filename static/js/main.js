
function logout() {
    $.get('/logout', function (resp) {
        location.reload()
    })
}