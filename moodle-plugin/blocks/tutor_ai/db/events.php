<?php
defined('MOODLE_INTERNAL') || die();

$observers = [
    [
        'eventname'   => '\core\event\course_module_created',
        'callback'    => 'block_tutor_ai_observer::course_module_created',
        'includefile' => '/blocks/tutor_ai/classes/observer.php',
        'internal'    => false,
    ],
];