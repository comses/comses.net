import 'fullcalendar'
import * as $ from 'jquery'

$(function() {
    $('#calendar').fullCalendar({
        customButtons: {
            addEventButton: {
                text: 'Add an event',
                click: function() {
                    window.location.href = '/events/add/';
                }
            }
        },
        height: 'auto',
        themeSystem: 'bootstrap4',
        header: {
            left: 'prev,next today',
            center: 'title addEventButton',
            right: 'month,agendaWeek,listMonth',
        },
        events: {
            'url': '/events/calendar/',
            'allDayDefault': true
        },
        eventRender: function(event, element) {
            let eventElement = element[0];
            eventElement.innerText = event.title;
        }
    })
})
