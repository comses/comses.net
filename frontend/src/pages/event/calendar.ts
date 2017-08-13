import 'fullcalendar'
import * as $ from 'jquery'

$(function() {
    $('#calendar').fullCalendar({
        events: {
            'url': '/events/calendar/',
            'allDayDefault': true
        },
        eventRender: function(event, element) {
            let eventElement = element[0];
            eventElement.setAttribute('data-toggle', 'tooltip');
            eventElement.setAttribute('title', event.title);
        }
    })
})