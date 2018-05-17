import {
  USER_CONNECTED,
  USER_DISCONNECTED,
  USER_DATA
} from '../action-creator.sync.js'

const defaultUser = {
  user_id: -1,
  logged: false,
  timezone: '',
  profile: {
    id: 1,
    slug: 'user'
  },
  email: '',
  is_active: true,
  caldav_url: null,
  avatar_url: null,
  created: '',
  display_name: ''
}

export default function user (state = defaultUser, action) {
  switch (action.type) {
    case `Set/${USER_CONNECTED}`:
      return action.user

    case `Set/${USER_DISCONNECTED}`:
      return defaultUser

    case `Update/${USER_DATA}`:
      return {...state, ...action.data}

    default:
      return state
  }
}
