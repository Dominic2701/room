# Beginner Code Guide

This project uses only Django templates, HTML, CSS, and JavaScript for the frontend.
There is no React, Vue, Node.js, or frontend build step.

## 1. How a page works

A page normally follows this path:

```text
URL -> Django view -> template -> CSS and JavaScript
```

Example for the rooms page:

```text
/rooms/
    booking/urls.py
        room_list()
            templates/rooms.html
                static/css/style.css
                static/js/script.js
```

The page URL is defined in [booking/urls.py](booking/urls.py).
The data is prepared by [booking/views.py](booking/views.py).
The visible HTML is in [templates/rooms.html](templates/rooms.html).

## 2. Important frontend files

| File | Purpose |
| --- | --- |
| [templates/base.html](templates/base.html) | Shared navigation, footer, CSS, and JavaScript links |
| [templates/home.html](templates/home.html) | Homepage and search form |
| [templates/rooms.html](templates/rooms.html) | Filters and room results |
| [templates/partials/room_card.html](templates/partials/room_card.html) | One reusable room card |
| [templates/room_detail.html](templates/room_detail.html) | One room's full details |
| [templates/booking.html](templates/booking.html) | Dates, guests, and payment method form |
| [templates/payment_checkout.html](templates/payment_checkout.html) | Payment provider step |
| [static/css/style.css](static/css/style.css) | All colors, spacing, layout, and responsive styles |
| [static/js/script.js](static/js/script.js) | Mobile menu, password button, and price calculation |

## 3. Django template syntax

Django templates mix normal HTML with special Django tags.

### Print a value

```html
<h1>{{ room.room_number }}</h1>
<p>{{ room.description }}</p>
```

`{{ ... }}` prints a value supplied by the Django view.

### Create a link

```html
<a href="{% url 'room_list' %}">View rooms</a>
```

`{% url 'room_list' %}` generates the correct URL from `booking/urls.py`.

### Add a condition

```html
{% if room.status == 'AVAILABLE' %}
  <a class="button" href="{% url 'book_room' room.pk %}">
    Book this room
  </a>
{% else %}
  <p>This room is unavailable.</p>
{% endif %}
```

### Repeat HTML for a list

```html
{% for room in rooms %}
  <h2>{{ room.get_room_type_display }}</h2>
{% empty %}
  <p>No rooms found.</p>
{% endfor %}
```

`{% empty %}` is displayed when the list has no items.

### Reuse a component

```html
{% include 'partials/room_card.html' with room=room %}
```

This keeps the room card in one file instead of copying it into multiple pages.

### Use the shared page layout

```html
{% extends 'base.html' %}

{% block title %}Rooms{% endblock %}

{% block content %}
  <h1>Rooms</h1>
{% endblock %}
```

`base.html` supplies the header and footer. The child page supplies the content block.

## 4. How the room search works

The form in [templates/home.html](templates/home.html) sends a GET request:

```html
<form action="{% url 'room_list' %}" method="get">
  <input type="date" name="check_in">
  <input type="date" name="check_out">
  <input type="number" name="capacity">
  <button type="submit">Search rooms</button>
</form>
```

The names are important:

- `check_in` becomes the check-in date
- `check_out` becomes the check-out date
- `capacity` becomes the guest count

Django reads these values in `room_list()` inside [booking/views.py](booking/views.py).

## 5. How CSS works

CSS selects HTML elements and changes their appearance.

```css
.room-card {
  background: #ffffff;
  padding: 20px;
  border: 1px solid #e0e5eb;
}
```

This styles every element with `class="room-card"`.

A class is connected like this:

```html
<article class="room-card">
  Room information
</article>
```

### Common CSS properties

```css
.card {
  display: grid;       /* controls layout */
  gap: 16px;           /* space between children */
  padding: 20px;       /* inside space */
  margin: 20px 0;      /* outside space */
  color: #1f2d3d;      /* text color */
  background: #ffffff; /* background color */
}
```

### Responsive design

The `@media (max-width: 800px)` section changes the layout for phones.
For example, a three-column room grid becomes one column.

## 6. How JavaScript works

[static/js/script.js](static/js/script.js) runs after the page loads.

The booking form has a price attribute:

```html
<form data-price="{{ room.price_per_night }}">
```

JavaScript reads that value and calculates:

```text
number of nights * price per night
```

Important security rule: JavaScript only improves the display. Django validates the dates, guests, room availability, payment, and booking on the server.

## 7. Safe beginner changes

### Change a heading

Edit the text inside the HTML tag:

```html
<h1>Choose your perfect stay.</h1>
```

### Change a button color

Find `.button` or `.card-button` in `static/css/style.css`:

```css
.card-button {
  background: #d84b36;
}
```

### Add a room-card label

Edit `templates/partials/room_card.html`:

```html
<span class="room-label">Available now</span>
```

Then add its appearance to the CSS:

```css
.room-label {
  color: #16805b;
  font-size: 12px;
  font-weight: 700;
}
```

## 8. Safe workflow after a frontend change

Run these commands from the project folder:

```powershell
python manage.py check
python manage.py test booking.tests
python manage.py runserver
```

Then open:

```text
http://127.0.0.1:8000/
```

If a template shows an `Invalid block tag` error, check that every opening Django tag has a matching closing tag:

```html
{% if something %}
  Content
{% endif %}
```

```html
{% for item in items %}
  Content
{% endfor %}
```

## 9. How the backend is organised

| File | Beginner explanation |
| --- | --- |
| [booking/models.py](booking/models.py) | Defines database tables such as rooms, bookings, users, and payments |
| [booking/forms.py](booking/forms.py) | Defines forms and validates user input |
| [booking/views.py](booking/views.py) | Contains the Python functions that respond to page requests |
| [booking/urls.py](booking/urls.py) | Connects a browser URL to a view function |
| [booking/admin.py](booking/admin.py) | Controls how models appear in Django admin |
| [booking/tests.py](booking/tests.py) | Checks that important workflows still work |
| [config/settings.py](config/settings.py) | Project settings, database, templates, and static files |

### Example: opening a room page

1. The browser requests `/rooms/3/`.
2. [booking/urls.py](booking/urls.py) sends that request to `room_detail`.
3. `room_detail` finds room number 3 using the Django ORM.
4. The view sends the room to [templates/room_detail.html](templates/room_detail.html).
5. The template displays the room using HTML and CSS.

```python
def room_detail(request, pk):
  room = get_object_or_404(Room, pk=pk)
  return render(request, "room_detail.html", {"room": room})
```

### Example: making a booking

1. The user submits [templates/booking.html](templates/booking.html).
2. `book_room` creates a `Booking` object after form validation.
3. Django saves the booking in the database.
4. A `Payment` object is created with a pending status.
5. The user continues to the payment page.
6. Only a successful payment changes the booking to confirmed.

The business rules belong in Python forms and views. JavaScript should only make the page more convenient; it should never be the only place where security or validation happens.
