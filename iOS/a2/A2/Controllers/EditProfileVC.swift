//
//  EditProfileVC.swift
//  A2
//
//  Created by Vin Bui on 6/4/23.
//
import UIKit

class EditProfileVC: UIViewController {
	
	private let profileImageView: UIImageView = {
		let imageView = UIImageView()
		imageView.translatesAutoresizingMaskIntoConstraints = false
		imageView.layer.cornerRadius = 40
		imageView.layer.masksToBounds = true
		imageView.image = UIImage(named: "profilePicture")
		return imageView
	}()
	
	private let nameTextField: UITextField = {
		let textField = UITextField()
		textField.translatesAutoresizingMaskIntoConstraints = false
		textField.placeholder = "Your Name"
		textField.borderStyle = .roundedRect
		return textField
	}()
	
	private let bioTextField: UITextField = {
		let textField = UITextField()
		textField.translatesAutoresizingMaskIntoConstraints = false
		textField.placeholder = "Your Bio"
		textField.borderStyle = .roundedRect
		return textField
	}()
	
	private let hometownTextField: UITextField = {
		let textField = UITextField()
		textField.translatesAutoresizingMaskIntoConstraints = false
		textField.placeholder = "Hometown"
		textField.borderStyle = .roundedRect
		return textField
	}()
	
	private let majorTextField: UITextField = {
		let textField = UITextField()
		textField.translatesAutoresizingMaskIntoConstraints = false
		textField.placeholder = "Major"
		textField.borderStyle = .roundedRect
		return textField
	}()
	
	private let saveButton: UIButton = {
		let button = UIButton()
		button.translatesAutoresizingMaskIntoConstraints = false
		button.setTitle("Save", for: .normal)
		button.setTitleColor(.white, for: .normal)
		button.backgroundColor = UIColor.a2.ruby
		button.layer.cornerRadius = 16
		button.addTarget(self, action: #selector(saveTapped), for: .touchUpInside)
		return button
	}()
	
	override func viewDidLoad() {
		super.viewDidLoad()
		view.backgroundColor = .white
		title = "Edit Profile"
		
		setupViews()
	}
	
	private func setupViews() {
		view.addSubview(profileImageView)
		view.addSubview(nameTextField)
		view.addSubview(bioTextField)
		view.addSubview(hometownTextField)
		view.addSubview(majorTextField)
		view.addSubview(saveButton)
		
		NSLayoutConstraint.activate([
			profileImageView.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 16),
			profileImageView.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 16),
			profileImageView.widthAnchor.constraint(equalToConstant: 80),
			profileImageView.heightAnchor.constraint(equalToConstant: 80),
			
			nameTextField.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 16),
			nameTextField.leadingAnchor.constraint(equalTo: profileImageView.trailingAnchor, constant: 16),
			nameTextField.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -16),
			nameTextField.heightAnchor.constraint(equalToConstant: 40),
			
			bioTextField.topAnchor.constraint(equalTo: nameTextField.bottomAnchor, constant: 16),
			bioTextField.leadingAnchor.constraint(equalTo: profileImageView.trailingAnchor, constant: 16),
			bioTextField.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -16),
			bioTextField.heightAnchor.constraint(equalToConstant: 40),
			
			hometownTextField.topAnchor.constraint(equalTo: profileImageView.bottomAnchor, constant: 16),
			hometownTextField.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 16),
			hometownTextField.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -16),
			hometownTextField.heightAnchor.constraint(equalToConstant: 40),
			
			majorTextField.topAnchor.constraint(equalTo: hometownTextField.bottomAnchor, constant: 16),
			majorTextField.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 16),
			majorTextField.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -16),
			majorTextField.heightAnchor.constraint(equalToConstant: 40),
			
			saveButton.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 32),
			saveButton.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -32),
			saveButton.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -32),
			saveButton.heightAnchor.constraint(equalToConstant: 56)
		])
	}
	
	@objc private func saveTapped() {
		navigationController?.popViewController(animated: true)
	}
}
