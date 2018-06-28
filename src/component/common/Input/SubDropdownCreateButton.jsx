import React from 'react'
import PropTypes from 'prop-types'

require('./SubDropdownCreateButton.styl')

const SubDropdownCreateButton = props => {
  return (
    <div>
      {props.availableApp.map(app =>
        <div className='subdropdown__link dropdown-item' onClick={e => props.onClickCreateContent(e, props.idFolder, app.slug)} key={app.slug}>
          <div className={`subdropdown__link__${app.slug} d-flex align-items-center`}>
            <div className={`subdropdown__link__${app.slug}__icon mr-3`}>
              <i className={`fa fa-fw fa-${app.faIcon}`} />
            </div>
            <div className='subdropdown__link__folder__text'>
              {app.creationLabel}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

SubDropdownCreateButton.propTypes = {
  availableApp: PropTypes.array.isRequired,
  onClickCreateContent: PropTypes.func.isRequired,
  idFolder: PropTypes.number
}

export default SubDropdownCreateButton
