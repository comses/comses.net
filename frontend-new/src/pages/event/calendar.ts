import 'fullcalendar';
import * as _$ from 'jquery';

const $: any = _$;

$(function() {
    $('#calendar').fullCalendar({
        customButtons: {
            addEventButton: {
                text: 'Add an event',
                click() {
                    window.location.href = '/events/add/';
                },
            },
        },
        height: 'auto',
        timezone: 'UTC',
        themeSystem: 'bootstrap4',
        nextDayThreshold: '00:00:00',
        header: {
            left: 'prev,next today',
            center: 'title addEventButton',
            right: 'month,agendaWeek,listMonth',
        },
        events: {
            url: '/events/calendar/',
            // 'allDayDefault': true,
        },
        eventRender(event, element) {
            const eventElement = element[0];
            eventElement.innerText = event.title;
        },
    });
});
