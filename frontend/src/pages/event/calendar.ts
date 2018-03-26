import 'fullcalendar'
import * as $ from 'jquery'

$(function() {
    $('#calendar').fullCalendar({
        height: 'auto',
        events: {
            'url': '/events/calendar/',
            'allDayDefault': true
        },
        eventRender: function(event, element) {
            let eventElement = element[0];
            eventElement.innerText = event.title;
            eventElement.setAttribute('data-toggle', 'tooltip');
            eventElement.setAttribute('title', event.title);
        }
    })
})