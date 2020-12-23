var empty_row;

function store_empty_row()
{
    last_row = get_last_row()
    empty_row = last_row.cloneNode(true)
}

function bind_events(parent)
{
    fields = parent.getElementsByTagName("input")
    for (field of fields) {
        if (field.type == 'text' || field.type == 'time') {
            field.addEventListener("change", add_blank_row_if_needed)
        }
    }

    document.getElementById("search-button").addEventListener("click", musicbrainz_search)

    document.forms.metadata.addEventListener("submit", function() {
        // Get the number of tracks
        // Doesn't matter if we count a blank row because it'll be discarded later on
        document.getElementById("numberOfTracks").value = document.getElementById("track-listing-table").getElementsByTagName("tbody")[0].getElementsByTagName("tr").length
    });
}

function add_blank_row_if_needed()
{
    last_row = get_last_row()
    fields = last_row.getElementsByTagName("input")
    last_row_empty = true
    for (field of fields) {
        if (field.value.trim() != "") {
            last_row_empty = false
            break;
        }
    }
    if (!last_row_empty) {
        // Create an empty row, update all the numbers and make sure the fields are empty
        tbody = document.getElementById("track-listing-table").getElementsByTagName("tbody")[0]
        new_row = empty_row.cloneNode(true)
        trackNumber = tbody.getElementsByTagName("tr").length+1
        new_row.getElementsByTagName("td")[0].innerHTML = trackNumber
        for (field of new_row.getElementsByTagName("input")) {
            prefix = field.name.substring(0, field.name.indexOf('_'))
            field.name = prefix + "_" + trackNumber
            field.value = ""
        }
        bind_events(new_row)
        tbody.appendChild(new_row)
    }
}

function get_last_row()
{
    table = document.getElementById("track-listing-table");
    rows = table.getElementsByTagName("tr");
    last_row = rows.item(rows.length-1);
    return last_row;
}

function musicbrainz_search()
{
    var form = document.forms.metadata
    var xhr = new XMLHttpRequest();
    xhr.addEventListener("load", function (e) {
        var response = JSON.parse(xhr.response)
        console.log(response)
        var panel = document.createElement("div")
        panel.className = "overlay"

        var heading = document.createElement("h2")
        heading.innerHTML = "Select release"
        panel.appendChild(heading)

        var list = document.createElement("ol")
        list.className = "release-list"

        for (release of response["release-list"]) {
            var listItem = document.createElement("li")
            listItem.dataset.releaseid = release.id
            var title = document.createElement("span")
            title.className = "title"
            // TODO: Support multiple artists
            if (release.hasOwnProperty("artist-credit") && release.hasOwnProperty("title")) {
                title.innerHTML = release["artist-credit"][0].name + " - " + release.title;
            } else if (release.hasOwnProperty("artist-credit")) {
                title.innerHTML = release["artist-credit"][0].name + " - UNTITLED RELEASE";
            } else if (release.hasOwnProperty("title")) {
                title.innerHTML = release.title
            }
            var year = document.createElement("span")
            year.className = "year"
            if (release.hasOwnProperty("date")) {
                year.innerHTML = "(" + release.date.substring(0, 4) + ")"
            }
            var country = document.createElement("span")
            country.className = "country"
            if (release.hasOwnProperty("country")) {
                country.innerHTML = release.country
            }

            listItem.appendChild(title)
            listItem.appendChild(year)
            listItem.appendChild(country)
            list.appendChild(listItem)
        }

        panel.appendChild(heading)
        panel.appendChild(list)
        document.body.appendChild(panel)

    });
    var url =
        "/search?artist=" + encodeURI(form.elements.albumartist.value) +
        "&release=" + encodeURI(form.elements.albumtitle.value) +
        "&date="+encodeURI(form.elements.albumyear.value)

    xhr.open("GET", url)
    xhr.send()
    return false;
}