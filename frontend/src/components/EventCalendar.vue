<template>
  <FullCalendar :options="calendarOptions" />
</template>

<script setup lang="ts">
import FullCalendar from "@fullcalendar/vue3";
import dayGridPlugin from "@fullcalendar/daygrid";
import timeGridPlugin from "@fullcalendar/timegrid";
import listPlugin from "@fullcalendar/list";
import bootstrap5Plugin from "@fullcalendar/bootstrap5";
import { useEventAPI } from "@/composables/api";

const { listCalendarEvents } = useEventAPI();

const calendarOptions = {
  plugins: [dayGridPlugin, timeGridPlugin, listPlugin, bootstrap5Plugin],
  customButtons: {
    add: {
      text: "Add an event",
      click() {
        window.location.href = "/events/add/";
      },
    },
  },
  height: "auto",
  timeZone: "local",
  themeSystem: "bootstrap5",
  nextDayThreshold: "00:00:00",
  headerToolbar: {
    start: "prev,next today",
    center: "title add",
    end: "dayGridMonth,timeGridWeek,listMonth",
  },
  events: async function (info: any, successCallback: any, failureCallback: any) {
    try {
      const events = await listCalendarEvents(info.start, info.end);
      successCallback(events);
    } catch (e) {
      failureCallback(e);
    }
  },
  eventContent: function (args: any) {
    const event = args.event;
    const eventElement = document.createElement("span");
    eventElement.innerText = event.title;
    return { domNodes: [eventElement] };
  },
};
</script>
