const mindMapSubtypeMap = {
    RESEARCH_ADVISOR_PI: {
        label: 'Research Advisor / PI',
        icon: 'fas fa-star',
    },
    THESIS_COMMITTEE: {
        label: 'Thesis Committee',
        icon: 'fas fa-vial',
    },
    OTHER_RESEARCH_TRAINEES: {
        label: 'Other Research Trainees',
        icon: 'fas fa-user-friends',
    },
    OTHER_RESEARCH_FACULTY: {
        label: 'Other Research Faculty',
        icon: 'fas fa-network-wired',
    },
    FAMILY_FRIENDS: {
        label: 'Family / Friends',
        icon: 'fas fa-heart',
    },
    OTHER_MENTORS: {
        label: 'Other Mentors',
        icon: 'fas fa-user-alt',
    },
};

export const EMPTY_MIND_MAP_SUBTYPE = {
    label: 'Select mentor type',
    icon: 'fas fa-question',
}

export default mindMapSubtypeMap;
