document.addEventListener('DOMContentLoaded', () => {
  const startDateWrapper = document.getElementById('start_date-wrapper');
  const startTimeWrapper = document.getElementById('start_time-wrapper');
  const dayofweekWrapper = document.getElementById('dayofweek-wrapper');
  const monthWrapper = document.getElementById('month-wrapper');
  const detailsWrapper = document.getElementById('details-wrapper');
  const monthDateWrapper = document.getElementById('month_date-wrapper');
  const dayWrapper = document.getElementById('day-wrapper');
  const weekWrapper = document.getElementById('week-wrapper');
  const everyWrapper = document.getElementById('every-wrapper');
  const timeperiodTypeField = document.getElementById('id_timeperiod_type');
  const monthDateField = document.getElementById('id_month_date');
  const dayofweekField = document.getElementById('id_dayofweek');
  const monthField = document.getElementById('id_month');

  const dayField = document.getElementById('id_day');
  const everyLabel = document.querySelector('label[for="id_every"]');

  if (!timeperiodTypeField || !monthDateField || !startDateWrapper || !detailsWrapper || !dayWrapper || !startTimeWrapper || !dayofweekWrapper || !weekWrapper || !monthWrapper || !monthDateWrapper || !everyWrapper || !everyLabel) {
    // Optionally log or bail early if the expected nodes aren’t present
    return;
  }

  const RECURRENCE_LABELS = {
    '2': 'Every day(s)',   // Daily
    '3': 'Every week(s)',  // Weekly
  };

  function toggle(el, show) {
    if (el) el.hidden = !show;
  }

  function toggleTimePeriodFields() {
    const val = timeperiodTypeField.value;
    const MonthDate = monthDateField.value;
   

    if (val === '0') { // One Time Only
      toggle(startDateWrapper, true);
      toggle(everyWrapper, false);
      toggle(dayofweekWrapper, false);
      toggle(monthWrapper, false);
      toggle(monthDateWrapper, false);
      toggle(dayWrapper, false);
      toggle(weekWrapper, false);
      toggle(detailsWrapper, false);
      dayofweekField.tomselect.clear();
      monthField.tomselect.clear();
    } else if (val === '2' ) { // Daily
      toggle(startDateWrapper, false);
      toggle(startTimeWrapper, true);
      toggle(dayofweekWrapper, false);
      toggle(monthWrapper, false);
      toggle(everyWrapper, true);
      toggle(monthDateWrapper, false);
      toggle(dayWrapper, false);
      toggle(weekWrapper, false);
      toggle(detailsWrapper, false);
    } else if (val === '3' ) { // Weekly
      toggle(startDateWrapper, false);
      toggle(startTimeWrapper, true);
      toggle(dayofweekWrapper, true);
      toggle(monthWrapper, false);
      toggle(everyWrapper, true);
      toggle(monthDateWrapper, false);
      toggle(dayWrapper, false);
      toggle(weekWrapper, false);
      toggle(detailsWrapper, true);
    } else if (val === '4') { // Monthly
      toggle(startDateWrapper, false);
      toggle(startTimeWrapper, true);
      toggle(dayofweekWrapper, false);
      toggle(monthWrapper, true);
      toggle(everyWrapper, false);
      toggle(monthDateWrapper, true);
      toggle(dayWrapper, true);
      toggle(weekWrapper, false);
      toggle(detailsWrapper, true);

      if (MonthDate === '1') { // Day of Month
        // Clear the Day of Week field, as the form will be invalid otherwise
        dayofweekField.tomselect.clear();
      };

      if (MonthDate === '2') { // Day of Week
        // Clear the Day field, as the form will be invalid otherwise
        dayField.value = null;
      };

    } else {
      // Fallback for any other value
      toggle(startDateWrapper, false);
      toggle(startTimeWrapper, false);
      toggle(dayofweekWrapper, false);
      toggle(monthWrapper, false);
      toggle(everyWrapper, false);
      toggle(monthDateWrapper, false);
      toggle(dayWrapper, false);
      toggle(weekWrapper, false);
      toggle(detailsWrapper, false);
    }

    // Label text
    everyLabel.textContent = RECURRENCE_LABELS[val] ?? 'Every day(s)'; // default if shown
  }

  function toggleMonthDateFields() {
    const timePeriod = timeperiodTypeField.value;
    const MonthDate = monthDateField.value;

    if (timePeriod === '4' && MonthDate === '1') { // Day of Month
      toggle(dayofweekWrapper, false);
      toggle(dayWrapper, true);
      toggle(weekWrapper, false);
      dayofweekField.tomselect.clear();
    } else if (timePeriod === '4' && MonthDate === '2') { // Day of week
      toggle(dayofweekWrapper, true);
      toggle(dayWrapper, false);
      toggle(weekWrapper, true);
      dayField.value = null;
    }
  }

  // Initial run
  toggleTimePeriodFields();
  toggleMonthDateFields();

  // React to changes
  timeperiodTypeField.addEventListener('change', toggleTimePeriodFields);
  monthDateField.addEventListener('change', toggleMonthDateFields);
});
